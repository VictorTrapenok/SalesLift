"""Проверки GraphQL-API через HTTP: контракт ошибок и сквозные сценарии.

Тесты бьют по приложению в процессе (httpx + ASGITransport), без реального
порта, но проходят весь путь: роутер → контекст → резолвер → сервис → БД.
"""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from saleslift.app import create_app
from saleslift.db.session import get_session

REGISTER_MUTATION = """
mutation Register($input: RegisterInput!) {
  resolverAuthRegister(input: $input) {
    token
    user { id name email effectivePermissions tenant { id name } }
  }
}
"""

LOGIN_MUTATION = """
mutation Login($input: LoginInput!) {
  resolverAuthLogin(input: $input) { token user { id email } }
}
"""

ME_QUERY = """
query Me { resolverAuthMe { id name email tenant { name } } }
"""


@pytest.fixture
async def client(db_engine: AsyncEngine) -> AsyncGenerator[AsyncClient]:
    """HTTP-клиент поверх приложения с сессией к тестовой БД."""
    app = create_app()

    async def _override_get_session() -> AsyncGenerator[Any]:
        async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
            yield s

    app.dependency_overrides[get_session] = _override_get_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _gql(
    client: AsyncClient,
    query: str,
    variables: dict[str, Any] | None = None,
    token: str | None = None,
    locale: str | None = None,
) -> dict[str, Any]:
    """Отправляет GraphQL-запрос и возвращает разобранный ответ."""
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if locale:
        headers["Accept-Language"] = locale

    response = await client.post(
        "/api/v1/graphql",
        json={"query": query, "variables": variables or {}},
        headers=headers,
    )
    assert response.status_code == 200
    result: dict[str, Any] = response.json()
    return result


def _register_vars(**overrides: str) -> dict[str, Any]:
    """Валидные переменные регистрации с уникальным e-mail."""
    return {
        "input": {
            "companyName": "ООО Ромашка",
            "adminName": "Иван Петров",
            "email": f"api-{uuid.uuid4().hex[:8]}@example.com",
            "password": "securePass123",
            "locale": "ru",
            **overrides,
        }
    }


class TestAuthFlow:
    """Сквозной сценарий: регистрация → логин → профиль."""

    async def test_регистрация_логин_и_профиль(self, client: AsyncClient) -> None:
        variables = _register_vars()

        registered = await _gql(client, REGISTER_MUTATION, variables)
        assert "errors" not in registered, registered
        payload = registered["data"]["resolverAuthRegister"]
        assert payload["user"]["tenant"]["name"] == "ООО Ромашка"

        logged_in = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": variables["input"]["email"], "password": "securePass123"}},
        )
        token = logged_in["data"]["resolverAuthLogin"]["token"]

        me = await _gql(client, ME_QUERY, token=token)
        assert me["data"]["resolverAuthMe"]["email"] == variables["input"]["email"]

    async def test_админ_получает_права_в_ответе(self, client: AsyncClient) -> None:
        """effectivePermissions типизированы enum'ом — это источник гейтинга UI."""
        result = await _gql(client, REGISTER_MUTATION, _register_vars())
        perms = result["data"]["resolverAuthRegister"]["user"]["effectivePermissions"]

        assert "Admin" in perms
        assert "Permission_users_see" in perms


class TestErrorContract:
    """Контракт ошибок — на него завязан фронтенд.

    Регрессия, которую эти тесты закрывают: гарды бросают доменные ошибки в
    обход резолвера, и при ручной обёртке клиент получал сырой ключ
    `auth.unauthenticated` без `extensions.code` и без перевода.
    """

    async def test_запрос_без_токена_возвращает_код_UNAUTHENTICATED(self, client: AsyncClient) -> None:
        result = await _gql(client, ME_QUERY)

        error = result["errors"][0]
        assert error["extensions"]["code"] == "UNAUTHENTICATED"

    async def test_ошибка_из_гарда_локализуется(self, client: AsyncClient) -> None:
        """Ошибка приходит из require_auth, а не из сервиса."""
        ru = await _gql(client, ME_QUERY, locale="ru-RU")
        en = await _gql(client, ME_QUERY, locale="en-US")

        assert ru["errors"][0]["message"] == "Требуется авторизация"
        assert en["errors"][0]["message"] == "Authentication required"

    async def test_сообщение_не_является_ключом_i18n(self, client: AsyncClient) -> None:
        """Именно так проявлялся баг: наружу уходил сырой ключ."""
        result = await _gql(client, ME_QUERY, locale="ru")
        assert "auth.unauthenticated" not in result["errors"][0]["message"]

    async def test_ошибка_валидации_несёт_имя_поля(self, client: AsyncClient) -> None:
        """`field` нужен фронтенду, чтобы подсветить конкретный инпут."""
        result = await _gql(client, REGISTER_MUTATION, _register_vars(password="1"), locale="ru")

        error = result["errors"][0]
        assert error["extensions"]["code"] == "BAD_USER_INPUT"
        assert error["extensions"]["field"] == "password"
        assert error["message"] == "Пароль должен быть не короче 8 символов"

    async def test_неверный_пароль_локализуется(self, client: AsyncClient) -> None:
        variables = _register_vars()
        await _gql(client, REGISTER_MUTATION, variables)

        result = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": variables["input"]["email"], "password": "wrongPass"}},
            locale="ru",
        )
        assert result["errors"][0]["extensions"]["code"] == "UNAUTHENTICATED"
        assert result["errors"][0]["message"] == "Неверный e-mail или пароль"

    async def test_битый_токен_не_роняет_публичные_операции(self, client: AsyncClient) -> None:
        """Протухший токен в заголовке не должен мешать залогиниться заново."""
        variables = _register_vars()
        await _gql(client, REGISTER_MUTATION, variables)

        result = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": variables["input"]["email"], "password": "securePass123"}},
            # Мусор вместо токена. Только ASCII: заголовки HTTP кириллицу не
            # переносят, да и настоящий JWT всегда base64.
            token="not.a.valid.token",
        )
        assert "errors" not in result
        assert result["data"]["resolverAuthLogin"]["token"]


class TestHealth:
    """Health доступен и без авторизации."""

    async def test_health_публичен(self, client: AsyncClient) -> None:
        result = await _gql(client, "{ health { status version build { branch } } }")
        assert result["data"]["health"]["status"] == "ok"
