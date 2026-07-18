"""GraphQL-тип сотрудника и регистрация enum'а прав в схеме."""

import uuid
from datetime import datetime

import strawberry

from saleslift.graphql.types.tenant import Tenant
from saleslift.models.user import User as UserModel
from saleslift.services.permissions import UserPermissions
from saleslift.services.users.user_roles_permission import get_effective_permissions, get_role_name

#: Регистрация enum прав в GraphQL-схеме.
#:
#: ЭТО И ЕСТЬ механизм доставки прав на фронтенд. Enum попадает в
#: schema.graphql при `make schema`, а graphql-codegen превращает его в
#: настоящий TypeScript-enum. Копировать файл, как в прототипе (`cp
#: permissions.ts`), не нужно — и рассинхрон становится невозможен: удалите
#: значение, на которое ссылается фронтенд, и codegen упадёт на сборке.
#:
#: `strawberry.enum` вызывается как обычная функция, а не декоратором, чтобы
#: `services/permissions.py` остался без единого импорта. Регистрация меняет
#: сам класс `UserPermissions`, поэтому в аннотациях ниже используется он же —
#: отдельный алиас mypy не принял бы за тип.
strawberry.enum(UserPermissions, name="UserPermissions")


@strawberry.type(description="Сотрудник компании")
class User:
    """Сотрудник в терминах API.

    Тип объявлен явно, а не выведен из ORM-модели автоматически. Это чуть
    больше кода, но контракт API перестаёт быть «какие колонки случайно есть у
    модели»: `password_hash` физически не может утечь в ответ, потому что его
    здесь просто нет.
    """

    id: uuid.UUID
    name: str
    email: str
    bio: str | None
    locale: str
    status: str
    last_login_at: datetime | None
    tenant: Tenant

    #: Маркер базовой роли (`admin`/`manager`/`viewer`) — ДЛЯ ПОКАЗА в списке
    #: сотрудников. Гейтить UI по нему нельзя: для этого есть
    #: `effective_permissions`. Отдаётся отдельным полем, чтобы фронтенд не
    #: выковыривал роль из `permissions`, где порядок ничего не значит.
    role: str

    #: Базовые записи из БД (`admin`/`manager`/`viewer` + точечные добавки).
    #: Для гейтинга UI использовать не это, а `effective_permissions`.
    permissions: list[str]

    #: Развёрнутый плоский список прав — единственный источник для гейтинга UI.
    #: Типизирован enum'ом, а не `[String!]!` как в прототипе: опечатка в праве
    #: становится ошибкой компиляции на фронтенде.
    effective_permissions: list[UserPermissions]

    @classmethod
    def from_model(cls, model: UserModel) -> "User":
        """Собирает GraphQL-тип из ORM-модели.

        Требует, чтобы связь `tenant` была уже загружена (`selectinload`):
        модели объявлены с `lazy="raise"`, поэтому забытый include упадёт
        явной ошибкой, а не тихим N+1.
        """
        return cls(
            id=model.id,
            name=model.name,
            email=model.email,
            bio=model.bio,
            locale=model.locale,
            status=model.status,
            last_login_at=model.last_login_at,
            tenant=Tenant.from_model(model.tenant),
            role=get_role_name(model),
            permissions=list(model.permissions),
            effective_permissions=get_effective_permissions(model),
        )


@strawberry.type(description="Результат успешной авторизации")
class AuthPayload:
    """Токен и профиль вошедшего сотрудника."""

    token: str
    user: User
