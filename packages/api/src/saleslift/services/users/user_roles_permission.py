"""Маппинг ролей на разрешения и гарды для резолверов.

Сам список разрешений — в `services/permissions.py` (файл без импортов и
логики). Здесь всё, что вокруг: во что разворачивается роль и как резолвер
проверяет доступ.

Подробности и ритуал добавления права — в user_roles_permission.md рядом.
"""

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from saleslift.models.tenant import Tenant
from saleslift.models.user import User
from saleslift.services.permissions import UserPermissions
from saleslift.utils.errors import AuthenticationError, ForbiddenError

if TYPE_CHECKING:
    from saleslift.graphql.context import Context

#: Во что разворачивается каждая базовая роль.
#:
#: Ролей три, но различаются пока только admin и остальные: списка сотрудников
#: и настроек компании достаточно, чтобы показать механику, а придумывать
#: разграничение под несуществующие фичи — гадание. Набор расширяется по мере
#: появления реальных действий.
USERS_ROLE_MAP: dict[str, list[UserPermissions]] = {
    "admin": [
        UserPermissions.Admin,
        UserPermissions.Manager,
        UserPermissions.Viewer,
        UserPermissions.Permission_users_see,
        UserPermissions.Permission_users_create,
        UserPermissions.Permission_users_edit,
        UserPermissions.Permission_users_delete,
        UserPermissions.Permission_org_settings_see,
        UserPermissions.Permission_org_settings_edit,
    ],
    "manager": [
        UserPermissions.Manager,
        UserPermissions.Viewer,
        UserPermissions.Permission_users_see,
        UserPermissions.Permission_org_settings_see,
    ],
    "viewer": [
        UserPermissions.Viewer,
        UserPermissions.Permission_users_see,
    ],
}


def get_effective_permissions(user: User | None) -> list[UserPermissions]:
    """Разворачивает `users.permissions` в плоский список разрешений.

    ЕДИНСТВЕННЫЙ допустимый способ читать права. Обращаться к
    `user.permissions[0]` нельзя: порядок записей в массиве ничего не значит,
    роль может стоять на любой позиции.

    Массив содержит маркер роли и опционально значения `UserPermissions`,
    точечно расширяющие роль. Неизвестные значения игнорируются: так
    выкатка, удаляющая право, не роняет вход пользователям, у которых оно
    ещё записано в БД.
    """
    if user is None:
        return []

    effective: set[UserPermissions] = set()
    for entry in user.permissions:
        if entry in USERS_ROLE_MAP:
            effective.update(USERS_ROLE_MAP[entry])
            continue
        try:
            effective.add(UserPermissions(entry))
        except ValueError:
            # Право удалили из кода, но оно осталось в БД — не повод ронять
            # запрос: просто игнорируем.
            continue

    # Сортировка по значению — чтобы порядок в GraphQL-ответе был стабилен и
    # не портил кэш Apollo на клиенте лишними изменениями.
    return sorted(effective, key=lambda p: p.value)


def get_role_name(user: User) -> str:
    """Возвращает маркер базовой роли из `users.permissions`.

    Нужен ровно для одного: показать роль в списке сотрудников. Для проверок
    доступа использовать нельзя — только `get_effective_permissions()`.

    Порядок записей в массиве значения не несёт, поэтому роль ищется
    перебором, а не по индексу. Если маркера нет вовсе (данные заведены в
    обход сервисов), возвращается самая слабая роль: показать «viewer» честнее,
    чем упасть на отрисовке таблицы.
    """
    for entry in user.permissions:
        if entry in USERS_ROLE_MAP:
            return entry
    return "viewer"


@dataclass(frozen=True)
class AuthenticatedContext:
    """Контекст запроса, про который ДОКАЗАНО, что пользователь есть.

    Отдельный тип, а не `cast` исходного контекста: mypy тогда сам проверяет,
    что защищённый резолвер не обращается к `current_user`, который мог бы
    оказаться None. Забыть гард становится ошибкой типов, а не багом.
    """

    user: User
    tenant: Tenant
    locale: str

    @property
    def tenant_id(self) -> uuid.UUID:
        """Идентификатор компании — им скоупится каждый запрос к БД."""
        return self.tenant.id


def require_auth(ctx: "Context") -> AuthenticatedContext:
    """Требует аутентификации. Бросает AuthenticationError, если её нет."""
    if ctx.current_user is None or ctx.tenant is None:
        raise AuthenticationError()
    return AuthenticatedContext(user=ctx.current_user, tenant=ctx.tenant, locale=ctx.locale)


def require_permission(ctx: "Context", permission: UserPermissions) -> AuthenticatedContext:
    """Требует конкретного разрешения. Бросает ForbiddenError, если его нет."""
    auth = require_auth(ctx)
    if permission not in get_effective_permissions(auth.user):
        raise ForbiddenError()
    return auth


def require_admin(ctx: "Context") -> AuthenticatedContext:
    """Требует роль администратора компании."""
    return require_permission(ctx, UserPermissions.Admin)
