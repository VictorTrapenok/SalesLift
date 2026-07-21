"""Резолверы списка сотрудников.

Тонкие адаптеры: гард → вызов сервиса → сборка ответа. Бизнес-логика —
в `services/users/users_service.py`.

Доменные ошибки не обрабатываются здесь: их перехватывает и локализует
`DomainErrorExtension`, подключённое к схеме.
"""

import uuid

import strawberry
from strawberry.types import Info

from saleslift.graphql.context import Context
from saleslift.graphql.types.user import User
from saleslift.services.permissions import UserPermissions
from saleslift.services.users import users_service as users_module
from saleslift.services.users.user_roles_permission import require_permission


@strawberry.input(description="Данные нового сотрудника")
class CreateEmployeeInput:
    """Поля формы «новый сотрудник».

    Пароль задаёт администратор и передаёт его сотруднику сам: приглашений по
    ссылке пока нет.
    """

    name: str
    email: str
    password: str
    #: Маркер базовой роли: `admin` / `manager` / `viewer`.
    role: str


@strawberry.input(description="Смена роли сотрудника")
class ChangeRoleInput:
    """Кому и какую роль назначить."""

    user_id: uuid.UUID
    #: Маркер базовой роли: `admin` / `manager` / `viewer`.
    role: str


@strawberry.input(description="Отключение или включение сотрудника")
class SetStatusInput:
    """Кому и какой статус выставить."""

    user_id: uuid.UUID
    #: `active` — вход разрешён, `suspended` — запрещён.
    status: str


@strawberry.input(description="Удаление сотрудника")
class DeleteEmployeeInput:
    """Кого удалить."""

    user_id: uuid.UUID


@strawberry.type
class UsersQuery:
    """Запросы по сотрудникам компании."""

    @strawberry.field(description="Список сотрудников компании")
    async def resolver_users_list(self, info: Info[Context, None]) -> list[User]:
        """Возвращает сотрудников компании вошедшего пользователя.

        Компания берётся из контекста, а не из аргументов: параметр tenantId
        здесь был бы дырой в изоляции тенантов.
        """
        auth = require_permission(info.context, UserPermissions.Permission_users_see)
        employees = await users_module.users_service.list_employees(info.context.session, auth.tenant_id)
        return [User.from_model(employee) for employee in employees]


@strawberry.type
class UsersMutation:
    """Изменения по сотрудникам компании."""

    @strawberry.mutation(description="Завести сотрудника в компании")
    async def resolver_users_create(self, info: Info[Context, None], input: CreateEmployeeInput) -> User:
        """Создаёт сотрудника с заданным паролем и ролью."""
        auth = require_permission(info.context, UserPermissions.Permission_users_create)
        employee = await users_module.users_service.create_employee(
            info.context.session,
            auth.tenant_id,
            users_module.CreateEmployeeInput(
                name=input.name,
                email=input.email,
                password=input.password,
                role=input.role,
                # Новый сотрудник получает язык того, кто его завёл: это
                # единственная известная о нём на момент создания подсказка.
                locale=auth.user.locale,
            ),
        )
        return User.from_model(employee)

    @strawberry.mutation(description="Сменить роль сотрудника")
    async def resolver_users_change_role(self, info: Info[Context, None], input: ChangeRoleInput) -> User:
        """Назначает сотруднику другую базовую роль."""
        auth = require_permission(info.context, UserPermissions.Permission_users_edit)
        employee = await users_module.users_service.change_role(
            info.context.session,
            auth.tenant_id,
            auth.user.id,
            input.user_id,
            input.role,
        )
        return User.from_model(employee)

    @strawberry.mutation(description="Отключить или включить сотрудника")
    async def resolver_users_set_status(self, info: Info[Context, None], input: SetStatusInput) -> User:
        """Запрещает или разрешает вход сотруднику."""
        auth = require_permission(info.context, UserPermissions.Permission_users_edit)
        employee = await users_module.users_service.set_status(
            info.context.session,
            auth.tenant_id,
            auth.user.id,
            input.user_id,
            input.status,
        )
        return User.from_model(employee)

    @strawberry.mutation(description="Удалить сотрудника")
    async def resolver_users_delete(self, info: Info[Context, None], input: DeleteEmployeeInput) -> User:
        """Мягко удаляет сотрудника компании."""
        auth = require_permission(info.context, UserPermissions.Permission_users_delete)
        employee = await users_module.users_service.delete_employee(
            info.context.session,
            auth.tenant_id,
            auth.user.id,
            input.user_id,
        )
        return User.from_model(employee)
