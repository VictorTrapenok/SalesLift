"""Интеграционные проверки собственного профиля: «о себе», язык, смена пароля."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.models import Tenant, User
from saleslift.services.auth.auth_service import hash_password, verify_password
from saleslift.services.users.profile_service import MAX_BIO_LENGTH, profile_service
from saleslift.utils.errors import ValidationError


@pytest.fixture
async def employee(session: AsyncSession, tenant: Tenant) -> User:
    """Сотрудник с известным паролем — им проверяется смена пароля."""
    user = User(
        tenant_id=tenant.id,
        name="Пётр Сидоров",
        email=f"profile-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("currentPass123"),
        permissions=["viewer"],
        status="active",
        locale="ru",
    )
    session.add(user)
    await session.commit()
    return user


class TestUpdateProfile:
    """Изменение собственного профиля."""

    async def test_сохраняет_имя_и_описание(self, session: AsyncSession, employee: User) -> None:
        updated = await profile_service.update_profile(
            session,
            employee,
            name="Пётр Сидоров-Петров",
            bio="Продаю с 2015 года",
            locale=None,
        )

        assert updated.name == "Пётр Сидоров-Петров"
        assert updated.bio == "Продаю с 2015 года"

    async def test_пустое_описание_становится_null(self, session: AsyncSession, employee: User) -> None:
        """Иначе «не заполнено» имело бы два разных представления в базе."""
        await profile_service.update_profile(session, employee, name="Пётр", bio="Текст", locale=None)

        updated = await profile_service.update_profile(session, employee, name="Пётр", bio="   ", locale=None)

        assert updated.bio is None

    async def test_язык_меняется(self, session: AsyncSession, employee: User) -> None:
        updated = await profile_service.update_profile(session, employee, name="Пётр", bio=None, locale="en")

        assert updated.locale == "en"

    async def test_язык_none_оставляет_прежний(self, session: AsyncSession, employee: User) -> None:
        updated = await profile_service.update_profile(session, employee, name="Пётр", bio=None, locale=None)

        assert updated.locale == "ru"

    async def test_неподдерживаемый_язык_отвергается(self, session: AsyncSession, employee: User) -> None:
        """В отличие от регистрации, здесь выбор явный — молча его игнорировать нельзя."""
        with pytest.raises(ValidationError) as err:
            await profile_service.update_profile(session, employee, name="Пётр", bio=None, locale="xx")

        assert err.value.i18n_key == "profile.unsupportedLocale"
        assert err.value.field == "locale"

    async def test_пустое_имя_отвергается(self, session: AsyncSession, employee: User) -> None:
        with pytest.raises(ValidationError) as err:
            await profile_service.update_profile(session, employee, name="   ", bio=None, locale=None)

        assert err.value.i18n_key == "auth.nameRequired"

    async def test_слишком_длинное_описание_отвергается(self, session: AsyncSession, employee: User) -> None:
        """Колонка TEXT без лимита — единственная проверка длины здесь."""
        with pytest.raises(ValidationError) as err:
            await profile_service.update_profile(
                session,
                employee,
                name="Пётр",
                bio="я" * (MAX_BIO_LENGTH + 1),
                locale=None,
            )

        assert err.value.i18n_key == "profile.bioTooLong"
        assert err.value.field == "bio"


class TestChangePassword:
    """Смена собственного пароля."""

    async def test_меняет_пароль(self, session: AsyncSession, employee: User) -> None:
        await profile_service.change_password(session, employee, "currentPass123", "brandNewPass456")

        assert employee.password_hash is not None
        assert verify_password("brandNewPass456", employee.password_hash)

    async def test_неверный_текущий_пароль_отвергается(self, session: AsyncSession, employee: User) -> None:
        """Иначе чужая незакрытая сессия позволяет забрать аккаунт себе."""
        with pytest.raises(ValidationError) as err:
            await profile_service.change_password(session, employee, "wrongPass", "brandNewPass456")

        assert err.value.i18n_key == "auth.wrongCurrentPassword"
        assert err.value.field == "currentPassword"

    async def test_неудачная_смена_не_меняет_пароль(self, session: AsyncSession, employee: User) -> None:
        original_hash = employee.password_hash

        with pytest.raises(ValidationError):
            await profile_service.change_password(session, employee, "wrongPass", "brandNewPass456")

        assert employee.password_hash == original_hash

    async def test_короткий_новый_пароль_отвергается(self, session: AsyncSession, employee: User) -> None:
        with pytest.raises(ValidationError) as err:
            await profile_service.change_password(session, employee, "currentPass123", "1234")

        assert err.value.i18n_key == "auth.passwordTooShort"
        assert err.value.field == "newPassword"

    async def test_сотрудник_без_пароля_не_меняет_его(self, session: AsyncSession, employee: User) -> None:
        """Пароля ещё нет (будущий флоу приглашений) — «сменить» его нельзя."""
        employee.password_hash = None
        await session.commit()

        with pytest.raises(ValidationError) as err:
            await profile_service.change_password(session, employee, "anything", "brandNewPass456")

        assert err.value.i18n_key == "auth.wrongCurrentPassword"
