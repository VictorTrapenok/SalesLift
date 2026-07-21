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


EMPLOYEES_QUERY = """
query Employees { resolverUsersList { id name email role } }
"""

CREATE_EMPLOYEE_MUTATION = """
mutation CreateEmployee($input: CreateEmployeeInput!) {
  resolverUsersCreate(input: $input) { id name email role }
}
"""

ORG_SETTINGS_UPDATE_MUTATION = """
mutation UpdateOrgSettings($input: UpdateOrgSettingsInput!) {
  resolverOrgSettingsUpdate(input: $input) { id name country }
}
"""

CHANGE_PASSWORD_MUTATION = """
mutation ChangePassword($input: ChangePasswordInput!) {
  resolverProfileChangePassword(input: $input) { id }
}
"""


async def _register_and_get_token(client: AsyncClient, **overrides: str) -> tuple[str, dict[str, Any]]:
    """Регистрирует компанию и возвращает токен её администратора."""
    variables = _register_vars(**overrides)
    result = await _gql(client, REGISTER_MUTATION, variables)
    assert "errors" not in result, result
    return result["data"]["resolverAuthRegister"]["token"], variables["input"]


class TestCabinetPages:
    """Страницы кабинета сквозь HTTP: сотрудники, настройки, профиль."""

    async def test_администратор_заводит_сотрудника_и_видит_его_в_списке(self, client: AsyncClient) -> None:
        token, _ = await _register_and_get_token(client)

        created = await _gql(
            client,
            CREATE_EMPLOYEE_MUTATION,
            {
                "input": {
                    "name": "Пётр Сидоров",
                    "email": f"emp-{uuid.uuid4().hex[:8]}@example.com",
                    "password": "securePass123",
                    "role": "manager",
                }
            },
            token=token,
        )
        assert "errors" not in created, created
        assert created["data"]["resolverUsersCreate"]["role"] == "manager"

        listed = await _gql(client, EMPLOYEES_QUERY, token=token)
        emails = [employee["email"] for employee in listed["data"]["resolverUsersList"]]
        assert created["data"]["resolverUsersCreate"]["email"] in emails

    async def test_список_не_протекает_между_компаниями(self, client: AsyncClient) -> None:
        """Изоляция тенантов — сквозная проверка, а не только на уровне сервиса."""
        _, first_admin = await _register_and_get_token(client)
        second_token, _ = await _register_and_get_token(client)

        listed = await _gql(client, EMPLOYEES_QUERY, token=second_token)

        emails = [employee["email"] for employee in listed["data"]["resolverUsersList"]]
        assert first_admin["email"] not in emails

    async def test_сотрудник_без_права_не_заводит_других(self, client: AsyncClient) -> None:
        """На каждое HasPermission на фронтенде — require_permission в резолвере."""
        admin_token, _ = await _register_and_get_token(client)
        viewer_email = f"viewer-{uuid.uuid4().hex[:8]}@example.com"

        await _gql(
            client,
            CREATE_EMPLOYEE_MUTATION,
            {"input": {"name": "Наблюдатель", "email": viewer_email, "password": "securePass123", "role": "viewer"}},
            token=admin_token,
        )
        viewer = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": viewer_email, "password": "securePass123"}},
        )
        viewer_token = viewer["data"]["resolverAuthLogin"]["token"]

        result = await _gql(
            client,
            CREATE_EMPLOYEE_MUTATION,
            {
                "input": {
                    "name": "Кто-то ещё",
                    "email": f"other-{uuid.uuid4().hex[:8]}@example.com",
                    "password": "securePass123",
                    "role": "viewer",
                }
            },
            token=viewer_token,
        )

        assert result["errors"][0]["extensions"]["code"] == "FORBIDDEN"

    async def test_настройки_компании_сохраняются(self, client: AsyncClient) -> None:
        token, _ = await _register_and_get_token(client)

        result = await _gql(
            client,
            ORG_SETTINGS_UPDATE_MUTATION,
            {"input": {"name": "ООО Незабудка", "country": "RU"}},
            token=token,
        )

        assert "errors" not in result, result
        assert result["data"]["resolverOrgSettingsUpdate"]["name"] == "ООО Незабудка"
        assert result["data"]["resolverOrgSettingsUpdate"]["country"] == "RU"

    async def test_смена_пароля_меняет_пароль_входа(self, client: AsyncClient) -> None:
        token, admin = await _register_and_get_token(client)

        changed = await _gql(
            client,
            CHANGE_PASSWORD_MUTATION,
            {"input": {"currentPassword": "securePass123", "newPassword": "brandNewPass456"}},
            token=token,
        )
        assert "errors" not in changed, changed

        with_old = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": admin["email"], "password": "securePass123"}},
        )
        with_new = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": admin["email"], "password": "brandNewPass456"}},
        )

        assert with_old["errors"][0]["extensions"]["code"] == "UNAUTHENTICATED"
        assert with_new["data"]["resolverAuthLogin"]["token"]

    async def test_неверный_текущий_пароль_несёт_имя_поля(self, client: AsyncClient) -> None:
        """`field` нужен фронтенду, чтобы подсветить конкретный инпут."""
        token, _ = await _register_and_get_token(client)

        result = await _gql(
            client,
            CHANGE_PASSWORD_MUTATION,
            {"input": {"currentPassword": "wrongPass", "newPassword": "brandNewPass456"}},
            token=token,
            locale="ru",
        )

        assert result["errors"][0]["extensions"]["field"] == "currentPassword"
        assert result["errors"][0]["message"] == "Текущий пароль указан неверно"


CHANGE_ROLE_MUTATION = """
mutation ChangeRole($input: ChangeRoleInput!) {
  resolverUsersChangeRole(input: $input) { id role }
}
"""

SET_STATUS_MUTATION = """
mutation SetStatus($input: SetStatusInput!) {
  resolverUsersSetStatus(input: $input) { id status }
}
"""

DELETE_EMPLOYEE_MUTATION = """
mutation DeleteEmployee($input: DeleteEmployeeInput!) {
  resolverUsersDelete(input: $input) { id }
}
"""


async def _create_employee(client: AsyncClient, admin_token: str, role: str) -> dict[str, Any]:
    """Заводит сотрудника и возвращает его узел из ответа."""
    result = await _gql(
        client,
        CREATE_EMPLOYEE_MUTATION,
        {
            "input": {
                "name": "Сотрудник",
                "email": f"emp-{uuid.uuid4().hex[:8]}@example.com",
                "password": "securePass123",
                "role": role,
            }
        },
        token=admin_token,
    )
    assert "errors" not in result, result
    node: dict[str, Any] = result["data"]["resolverUsersCreate"]
    return node


class TestEmployeeManagement:
    """Управление сотрудниками сквозь HTTP: роль, статус, удаление."""

    async def test_администратор_меняет_роль(self, client: AsyncClient) -> None:
        admin_token, _ = await _register_and_get_token(client)
        employee = await _create_employee(client, admin_token, "viewer")

        result = await _gql(
            client,
            CHANGE_ROLE_MUTATION,
            {"input": {"userId": employee["id"], "role": "manager"}},
            token=admin_token,
        )

        assert result["data"]["resolverUsersChangeRole"]["role"] == "manager"

    async def test_отключённый_сотрудник_не_может_войти(self, client: AsyncClient) -> None:
        """Статус читается на каждом запросе — отключение действует сразу."""
        admin_token, _ = await _register_and_get_token(client)
        employee = await _create_employee(client, admin_token, "manager")

        # Узнаём e-mail заведённого: он в списке.
        listed = await _gql(client, EMPLOYEES_QUERY, token=admin_token)
        email = next(e["email"] for e in listed["data"]["resolverUsersList"] if e["id"] == employee["id"])

        suspended = await _gql(
            client,
            SET_STATUS_MUTATION,
            {"input": {"userId": employee["id"], "status": "suspended"}},
            token=admin_token,
        )
        assert suspended["data"]["resolverUsersSetStatus"]["status"] == "suspended"

        login = await _gql(client, LOGIN_MUTATION, {"input": {"email": email, "password": "securePass123"}})
        assert login["errors"][0]["extensions"]["code"] == "UNAUTHENTICATED"

    async def test_удалённый_сотрудник_пропадает_из_списка(self, client: AsyncClient) -> None:
        admin_token, _ = await _register_and_get_token(client)
        employee = await _create_employee(client, admin_token, "viewer")

        deleted = await _gql(
            client,
            DELETE_EMPLOYEE_MUTATION,
            {"input": {"userId": employee["id"]}},
            token=admin_token,
        )
        assert "errors" not in deleted, deleted

        listed = await _gql(client, EMPLOYEES_QUERY, token=admin_token)
        assert employee["id"] not in [e["id"] for e in listed["data"]["resolverUsersList"]]

    async def test_менеджер_не_может_менять_роли(self, client: AsyncClient) -> None:
        """На каждое HasPermission на фронтенде — require_permission в резолвере."""
        admin_token, _ = await _register_and_get_token(client)
        manager = await _create_employee(client, admin_token, "manager")
        victim = await _create_employee(client, admin_token, "viewer")

        listed = await _gql(client, EMPLOYEES_QUERY, token=admin_token)
        manager_email = next(e["email"] for e in listed["data"]["resolverUsersList"] if e["id"] == manager["id"])
        manager_login = await _gql(
            client,
            LOGIN_MUTATION,
            {"input": {"email": manager_email, "password": "securePass123"}},
        )
        manager_token = manager_login["data"]["resolverAuthLogin"]["token"]

        result = await _gql(
            client,
            CHANGE_ROLE_MUTATION,
            {"input": {"userId": victim["id"], "role": "admin"}},
            token=manager_token,
        )

        assert result["errors"][0]["extensions"]["code"] == "FORBIDDEN"

    async def test_нельзя_удалить_чужого_сотрудника(self, client: AsyncClient) -> None:
        """Сквозная проверка изоляции: чужой id недоступен даже администратору."""
        first_token, _ = await _register_and_get_token(client)
        second_token, _ = await _register_and_get_token(client)
        alien = await _create_employee(client, first_token, "viewer")

        result = await _gql(
            client,
            DELETE_EMPLOYEE_MUTATION,
            {"input": {"userId": alien["id"]}},
            token=second_token,
        )

        assert result["errors"][0]["extensions"]["code"] == "NOT_FOUND"

    async def test_нельзя_удалить_себя(self, client: AsyncClient) -> None:
        admin_token, _ = await _register_and_get_token(client)
        me = await _gql(client, "query { resolverAuthMe { id } }", token=admin_token)
        my_id = me["data"]["resolverAuthMe"]["id"]

        result = await _gql(
            client,
            DELETE_EMPLOYEE_MUTATION,
            {"input": {"userId": my_id}},
            token=admin_token,
            locale="ru",
        )

        assert result["errors"][0]["extensions"]["code"] == "BAD_USER_INPUT"
        assert result["errors"][0]["message"] == "Свою учётную запись здесь менять нельзя"
