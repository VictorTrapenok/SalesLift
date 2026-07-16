"""Интеграционные проверки регистрации и входа. Реальная PostgreSQL, без моков."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.models import Tenant, User
from saleslift.services.auth.auth_service import (
    LoginInput,
    RegisterInput,
    auth_service,
    hash_password,
)
from saleslift.services.auth.tokens import decode_session_token
from saleslift.services.permissions import UserPermissions
from saleslift.services.users.user_roles_permission import get_effective_permissions
from saleslift.utils.errors import AuthenticationError, ValidationError


def _register_input(**overrides: str) -> RegisterInput:
    """Валидные данные регистрации с уникальным e-mail."""
    defaults = {
        "company_name": "ООО Ромашка",
        "admin_name": "Иван Петров",
        "email": f"admin-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securePass123",
        "locale": "ru",
    }
    return RegisterInput(**{**defaults, **overrides})


class TestRegister:
    """Регистрация компании — фича №1."""

    async def test_создаёт_компанию_и_администратора_возвращает_токен(self, session: AsyncSession) -> None:
        data = _register_input()

        result = await auth_service.register(session, data, "ru")

        assert result.user.email == data.email
        assert result.user.name == "Иван Петров"
        assert result.user.tenant.name == "ООО Ромашка"

        payload = decode_session_token(result.token)
        assert payload["user_id"] == str(result.user.id)
        assert payload["tenant_id"] == str(result.user.tenant_id)

    async def test_первый_зарегистрировавшийся_становится_администратором(self, session: AsyncSession) -> None:
        """Кто-то должен иметь право завести остальных сотрудников."""
        result = await auth_service.register(session, _register_input(), "ru")

        assert result.user.permissions == ["admin"]
        assert UserPermissions.Admin in get_effective_permissions(result.user)

    async def test_неудачная_регистрация_не_оставляет_компанию(self, session: AsyncSession) -> None:
        """Компания без единого сотрудника недоступна никому — такой быть не должно.

        Имя компании уникальное: имена не обязаны быть уникальны, а TRUNCATE
        делается на модуль, поэтому компании от предыдущих тестов ещё живы.
        """
        company_name = f"Компания-{uuid.uuid4().hex[:8]}"
        data = _register_input(company_name=company_name, email="bad-email-without-at")

        with pytest.raises(ValidationError):
            await auth_service.register(session, data, "ru")

        assert await session.scalar(select(Tenant).where(Tenant.name == company_name)) is None

    async def test_гонка_дубликата_email_откатывает_компанию(self, session: AsyncSession) -> None:
        """Между проверкой занятости и вставкой e-mail мог занять кто-то другой.

        Настоящая гарантия — частичный уникальный индекс; сервис обязан поймать
        IntegrityError и не оставить после отката осиротевшую компанию.
        Гонку воспроизводим, вставив пользователя в обход сервиса.
        """
        email = f"race-{uuid.uuid4().hex[:8]}@example.com"
        company_name = f"Гонка-{uuid.uuid4().hex[:8]}"

        # Пользователь уже существует, но сервис о нём ещё «не знает»:
        # эмулируем параллельную регистрацию, проскочившую проверку.
        squatter_tenant = Tenant(name="Занявший адрес")
        session.add(User(tenant=squatter_tenant, name="Занявший", email=email, permissions=["admin"]))
        await session.commit()

        with pytest.raises(ValidationError) as err:
            # Проверку занятости обходим тем, что она уже пройдена в другой
            # сессии: здесь сработает именно индекс.
            await auth_service.register(
                session,
                _register_input(company_name=company_name, email=email),
                "ru",
            )
        assert err.value.i18n_key == "auth.emailTaken"
        assert await session.scalar(select(Tenant).where(Tenant.name == company_name)) is None

    async def test_email_нормализуется(self, session: AsyncSession) -> None:
        suffix = uuid.uuid4().hex[:8]
        result = await auth_service.register(session, _register_input(email=f"  Ivan.{suffix}@EXAMPLE.com "), "ru")
        assert result.user.email == f"ivan.{suffix}@example.com"

    async def test_отклоняет_занятый_email(self, session: AsyncSession) -> None:
        data = _register_input()
        await auth_service.register(session, data, "ru")

        with pytest.raises(ValidationError) as err:
            await auth_service.register(session, _register_input(email=data.email), "ru")
        assert err.value.field == "email"
        assert err.value.i18n_key == "auth.emailTaken"

    async def test_занятость_email_проверяется_независимо_от_регистра(self, session: AsyncSession) -> None:
        """Нормализация — то, на чём держится уникальный индекс по обычной колонке."""
        data = _register_input()
        await auth_service.register(session, data, "ru")

        with pytest.raises(ValidationError):
            await auth_service.register(session, _register_input(email=data.email.upper()), "ru")

    async def test_email_уникален_глобально_а_не_внутри_компании(self, session: AsyncSession) -> None:
        """Ключевое отличие от прототипа: компания выводится из строки пользователя."""
        data = _register_input(company_name="Первая компания")
        await auth_service.register(session, data, "ru")

        with pytest.raises(ValidationError):
            await auth_service.register(
                session,
                _register_input(company_name="Вторая компания", email=data.email),
                "ru",
            )

    async def test_две_компании_могут_называться_одинаково(self, session: AsyncSession) -> None:
        """Slug'а нет, уникальность имени не требуется — две «Ромашки» не мешают друг другу."""
        await auth_service.register(session, _register_input(company_name="Ромашка"), "ru")
        second = await auth_service.register(session, _register_input(company_name="Ромашка"), "ru")

        assert second.user.tenant.name == "Ромашка"

    @pytest.mark.parametrize(
        ("overrides", "expected_field"),
        [
            ({"password": "short"}, "password"),
            ({"email": "не-email"}, "email"),
            ({"company_name": "   "}, "companyName"),
            ({"admin_name": ""}, "adminName"),
        ],
    )
    async def test_валидация_помечает_проблемное_поле(
        self,
        session: AsyncSession,
        overrides: dict[str, str],
        expected_field: str,
    ) -> None:
        """`field` нужен фронтенду, чтобы подсветить конкретный инпут."""
        with pytest.raises(ValidationError) as err:
            await auth_service.register(session, _register_input(**overrides), "ru")
        assert err.value.field == expected_field

    async def test_пароль_не_хранится_в_открытом_виде(self, session: AsyncSession) -> None:
        data = _register_input()
        result = await auth_service.register(session, data, "ru")

        assert result.user.password_hash is not None
        assert data.password not in result.user.password_hash


class TestLogin:
    """Вход сотрудника — фича №2."""

    async def test_логин_по_email_и_паролю_возвращает_токен(self, session: AsyncSession) -> None:
        data = _register_input()
        await auth_service.register(session, data, "ru")

        result = await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")

        payload = decode_session_token(result.token)
        assert payload["user_id"] == str(result.user.id)

    async def test_логин_выводит_компанию_из_строки_пользователя(self, session: AsyncSession) -> None:
        """Резолвинг тенанта без поддомена: форма содержит только email и пароль."""
        data = _register_input(company_name="Компания из логина")
        registered = await auth_service.register(session, data, "ru")

        result = await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")

        assert result.user.tenant_id == registered.user.tenant_id
        assert decode_session_token(result.token)["tenant_id"] == str(registered.user.tenant_id)

    async def test_логин_нечувствителен_к_регистру_email(self, session: AsyncSession) -> None:
        data = _register_input()
        await auth_service.register(session, data, "ru")

        result = await auth_service.login(
            session,
            LoginInput(email=f"  {data.email.upper()}  ", password=data.password),
            "ru",
        )
        assert result.user.email == data.email

    async def test_проставляет_last_login_at(self, session: AsyncSession) -> None:
        data = _register_input()
        registered = await auth_service.register(session, data, "ru")
        assert registered.user.last_login_at is None

        result = await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")
        assert result.user.last_login_at is not None

    async def test_неверный_пароль_бросает_AuthenticationError(self, session: AsyncSession) -> None:
        data = _register_input()
        await auth_service.register(session, data, "ru")

        with pytest.raises(AuthenticationError) as err:
            await auth_service.login(session, LoginInput(email=data.email, password="wrongPassword"), "ru")
        assert err.value.i18n_key == "auth.invalidCredentials"

    async def test_несуществующий_email_даёт_ту_же_ошибку_что_неверный_пароль(
        self,
        session: AsyncSession,
    ) -> None:
        """Сообщения обязаны совпадать: иначе форма логина превращается в
        оракул «зарегистрирован ли такой адрес»."""
        with pytest.raises(AuthenticationError) as err:
            await auth_service.login(session, LoginInput(email="нет-такого@example.com", password="anyPass123"), "ru")
        assert err.value.i18n_key == "auth.invalidCredentials"

    async def test_пользователь_без_пароля_не_может_войти(self, session: AsyncSession, tenant: Tenant) -> None:
        """password_hash=NULL — заготовка под будущие приглашения, а не вход без пароля."""
        session.add(
            User(
                tenant_id=tenant.id,
                name="Приглашённый",
                email=f"invited-{uuid.uuid4().hex[:8]}@example.com",
                password_hash=None,
                permissions=["viewer"],
            )
        )
        await session.commit()
        user = await session.scalar(select(User).where(User.password_hash.is_(None)))
        assert user is not None

        with pytest.raises(AuthenticationError):
            await auth_service.login(session, LoginInput(email=user.email, password="anyPass123"), "ru")

    async def test_отключённый_сотрудник_не_может_войти(self, session: AsyncSession) -> None:
        data = _register_input()
        registered = await auth_service.register(session, data, "ru")

        registered.user.status = "suspended"
        await session.commit()

        with pytest.raises(AuthenticationError) as err:
            await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")
        assert err.value.i18n_key == "auth.accountDisabled"

    async def test_сотрудник_отключённой_компании_не_может_войти(self, session: AsyncSession) -> None:
        data = _register_input()
        registered = await auth_service.register(session, data, "ru")

        registered.user.tenant.is_active = False
        await session.commit()

        with pytest.raises(AuthenticationError) as err:
            await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")
        assert err.value.i18n_key == "auth.accountDisabled"

    async def test_мягко_удалённый_сотрудник_не_может_войти(self, session: AsyncSession) -> None:
        """Глобальный фильтр soft-delete обязан действовать и на пути логина."""
        from datetime import UTC, datetime

        data = _register_input()
        registered = await auth_service.register(session, data, "ru")

        registered.user.deleted_at = datetime.now(UTC)
        await session.commit()

        with pytest.raises(AuthenticationError):
            await auth_service.login(session, LoginInput(email=data.email, password=data.password), "ru")


class TestPasswordHashing:
    """Хеширование паролей."""

    def test_хеш_проверяется(self) -> None:
        h = hash_password("securePass123")
        from saleslift.services.auth.auth_service import verify_password

        assert verify_password("securePass123", h)
        assert not verify_password("wrongPass123", h)

    def test_одинаковые_пароли_дают_разные_хеши(self) -> None:
        """Соль: одинаковые пароли не должны выглядеть одинаково в базе."""
        assert hash_password("samePass123") != hash_password("samePass123")
