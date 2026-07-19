"""Интеграционные проверки списка сотрудников и их заведения.

Реальная PostgreSQL, без моков.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.models import Tenant
from saleslift.services.permissions import UserPermissions
from saleslift.services.users.user_roles_permission import get_effective_permissions, get_role_name
from saleslift.services.users.users_service import CreateEmployeeInput, users_service
from saleslift.utils.errors import ValidationError


def _employee_input(**overrides: str) -> CreateEmployeeInput:
    """Валидные данные нового сотрудника с уникальным e-mail."""
    defaults = {
        "name": "Пётр Сидоров",
        "email": f"employee-{uuid.uuid4().hex[:8]}@example.com",
        "password": "securePass123",
        "role": "manager",
        "locale": "ru",
    }
    return CreateEmployeeInput(**{**defaults, **overrides})


class TestCreateEmployee:
    """Заведение сотрудника администратором."""

    async def test_создаёт_сотрудника_с_заданной_ролью(self, session: AsyncSession, tenant: Tenant) -> None:
        data = _employee_input()

        employee = await users_service.create_employee(session, tenant.id, data)

        assert employee.email == data.email
        assert employee.tenant_id == tenant.id
        assert employee.status == "active"
        assert get_role_name(employee) == "manager"
        assert UserPermissions.Manager in get_effective_permissions(employee)

    async def test_пароль_сохраняется_хешем(self, session: AsyncSession, tenant: Tenant) -> None:
        """Пароль задаёт администратор — в базе он всё равно обязан быть хешем."""
        employee = await users_service.create_employee(session, tenant.id, _employee_input())

        assert employee.password_hash is not None
        assert employee.password_hash != "securePass123"

    async def test_email_нормализуется(self, session: AsyncSession, tenant: Tenant) -> None:
        employee = await users_service.create_employee(
            session,
            tenant.id,
            _employee_input(email=f"  MiXeD-{uuid.uuid4().hex[:8]}@Example.COM  "),
        )

        assert employee.email == employee.email.strip().lower()

    async def test_занятый_email_отвергается(self, session: AsyncSession, tenant: Tenant) -> None:
        data = _employee_input()
        await users_service.create_employee(session, tenant.id, data)

        with pytest.raises(ValidationError) as err:
            await users_service.create_employee(session, tenant.id, _employee_input(email=data.email))

        assert err.value.i18n_key == "users.emailTaken"
        assert err.value.field == "email"

    async def test_email_занятый_в_чужой_компании_тоже_отвергается(
        self,
        session: AsyncSession,
        tenant: Tenant,
        other_tenant: Tenant,
    ) -> None:
        """E-mail уникален ГЛОБАЛЬНО: на нём резолвится компания при входе."""
        data = _employee_input()
        await users_service.create_employee(session, other_tenant.id, data)

        with pytest.raises(ValidationError) as err:
            await users_service.create_employee(session, tenant.id, _employee_input(email=data.email))

        assert err.value.i18n_key == "users.emailTaken"

    async def test_неизвестная_роль_отвергается(self, session: AsyncSession, tenant: Tenant) -> None:
        """Иначе сотрудник получил бы пустой набор прав и молча ничего не мог."""
        with pytest.raises(ValidationError) as err:
            await users_service.create_employee(session, tenant.id, _employee_input(role="superuser"))

        assert err.value.i18n_key == "users.invalidRole"
        assert err.value.field == "role"

    @pytest.mark.parametrize(
        ("overrides", "expected_key"),
        [
            ({"name": "   "}, "auth.nameRequired"),
            ({"email": "не-почта"}, "auth.invalidEmail"),
            ({"password": "1234"}, "auth.passwordTooShort"),
        ],
    )
    async def test_невалидные_данные_отвергаются(
        self,
        session: AsyncSession,
        tenant: Tenant,
        overrides: dict[str, str],
        expected_key: str,
    ) -> None:
        with pytest.raises(ValidationError) as err:
            await users_service.create_employee(session, tenant.id, _employee_input(**overrides))

        assert err.value.i18n_key == expected_key


class TestListEmployees:
    """Список сотрудников компании."""

    async def test_возвращает_сотрудников_своей_компании_по_алфавиту(
        self,
        session: AsyncSession,
        tenant: Tenant,
    ) -> None:
        await users_service.create_employee(session, tenant.id, _employee_input(name="Яков"))
        await users_service.create_employee(session, tenant.id, _employee_input(name="Анна"))

        employees = await users_service.list_employees(session, tenant.id)

        names = [employee.name for employee in employees]
        assert names == sorted(names)
        assert {"Анна", "Яков"} <= set(names)

    async def test_не_видит_сотрудников_чужой_компании(
        self,
        session: AsyncSession,
        tenant: Tenant,
        other_tenant: Tenant,
    ) -> None:
        """Изоляция тенантов держится на явном where, а значит — на этом тесте."""
        await users_service.create_employee(session, other_tenant.id, _employee_input(name="Чужой сотрудник"))
        await users_service.create_employee(session, tenant.id, _employee_input(name="Свой сотрудник"))

        employees = await users_service.list_employees(session, tenant.id)

        assert [employee.name for employee in employees] == ["Свой сотрудник"]
        assert all(employee.tenant_id == tenant.id for employee in employees)

    async def test_компания_загружена_и_не_даёт_n_плюс_1(self, session: AsyncSession, tenant: Tenant) -> None:
        """Связи объявлены с lazy="raise": забытый selectinload упал бы здесь."""
        await users_service.create_employee(session, tenant.id, _employee_input())

        employees = await users_service.list_employees(session, tenant.id)

        assert all(employee.tenant.id == tenant.id for employee in employees)

    async def test_не_показывает_мягко_удалённых(self, session: AsyncSession, tenant: Tenant) -> None:
        """Фильтрация включена глобальным слушателем — проверяем, что она работает."""
        employee = await users_service.create_employee(session, tenant.id, _employee_input(name="Уволенный"))
        deleted_id = employee.id

        # Мягкое удаление руками: сервиса удаления сотрудника ещё нет, а
        # проверить фильтрацию нужно уже сейчас.
        employee.deleted_at = datetime.now(UTC)
        await session.commit()

        employees = await users_service.list_employees(session, tenant.id)

        assert deleted_id not in [employee.id for employee in employees]
