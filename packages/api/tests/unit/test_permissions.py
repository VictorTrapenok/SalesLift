"""Проверки маппинга ролей и разворачивания прав."""

import uuid

from saleslift.models.user import User
from saleslift.services.permissions import UserPermissions
from saleslift.services.users.user_roles_permission import (
    USERS_ROLE_MAP,
    get_effective_permissions,
)


def _make_user(permissions: list[str]) -> User:
    """Собирает пользователя в памяти, без записи в БД."""
    return User(
        tenant_id=uuid.uuid4(),
        name="Тест",
        email="test@example.com",
        permissions=permissions,
    )


def test_все_роли_разворачиваются_в_известные_права() -> None:
    """Опечатка в USERS_ROLE_MAP не должна доживать до рантайма."""
    for role, perms in USERS_ROLE_MAP.items():
        for perm in perms:
            assert isinstance(perm, UserPermissions), f"роль {role!r} ссылается на неизвестное право {perm!r}"


def test_админ_получает_все_права() -> None:
    effective = get_effective_permissions(_make_user(["admin"]))
    assert set(effective) == set(UserPermissions)


def test_viewer_не_может_менять_настройки() -> None:
    effective = get_effective_permissions(_make_user(["viewer"]))
    assert UserPermissions.Permission_users_see in effective
    assert UserPermissions.Permission_org_settings_edit not in effective
    assert UserPermissions.Permission_users_create not in effective


def test_гранулярное_право_расширяет_роль() -> None:
    """Массив прав = маркер роли + точечные добавки сверх неё."""
    effective = get_effective_permissions(_make_user(["viewer", "Permission_org_settings_see"]))
    assert UserPermissions.Permission_org_settings_see in effective
    assert UserPermissions.Permission_org_settings_edit not in effective


def test_роль_ищется_не_по_первому_элементу() -> None:
    """Порядок в массиве прав ничего не значит."""
    first = get_effective_permissions(_make_user(["admin", "Permission_users_see"]))
    second = get_effective_permissions(_make_user(["Permission_users_see", "admin"]))
    assert set(first) == set(second)


def test_неизвестное_право_из_бд_игнорируется() -> None:
    """Право удалили из кода, но в БД оно осталось — вход ломаться не должен."""
    effective = get_effective_permissions(_make_user(["viewer", "Permission_удалённое_право"]))
    assert UserPermissions.Viewer in effective


def test_без_пользователя_прав_нет() -> None:
    assert get_effective_permissions(None) == []


def test_порядок_прав_стабилен() -> None:
    """Нестабильный порядок ломал бы кэш Apollo на клиенте на ровном месте."""
    user = _make_user(["admin"])
    assert get_effective_permissions(user) == get_effective_permissions(user)
