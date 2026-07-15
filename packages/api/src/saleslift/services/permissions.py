"""Единый источник истины для гранулярных разрешений системы.

ВАЖНО: файл не должен содержать ни импортов, ни логики — только объявление
enum. Маппинг ролей на разрешения и runtime-проверки живут отдельно, в
`services/users/user_roles_permission.py`.

Как значения попадают на фронтенд
---------------------------------
Через GraphQL-схему, а не копированием файла. Enum регистрируется в схеме
(`graphql/types/user.py`), уезжает в `schema.graphql` при `make schema`, и
graphql-codegen превращает его в настоящий TypeScript-enum в
`packages/web/src/graphql/generated/`. Отдельная синхронизация не нужна:
рассинхрон невозможен by construction — удалишь значение, на которое ссылается
фронтенд, и `npm run codegen` упадёт на сборке.

Структура значений
------------------
- `Viewer` / `Manager` / `Admin` — маркеры базовой роли. Проверяются, когда
  нужно именно «является ли администратором», а не конкретное действие.
- `Permission_<scope>_<action>` — гранулярные разрешения, по одному на действие
  из резолверов. Их проверяют и бэкенд, и фронтенд.

При добавлении нового разрешения
--------------------------------
1. Добавь значение в этот enum.
2. Пропиши его в `USERS_ROLE_MAP` в `user_roles_permission.py`.
3. Используй в резолвере: `require_permission(ctx, UserPermissions.X)`.
4. Запусти `make codegen` — enum на фронтенде обновится сам.
"""

from enum import StrEnum


class UserPermissions(StrEnum):
    """Гранулярные разрешения и маркеры ролей."""

    # ── Маркеры базовых ролей ────────────────────────────────────────────
    Viewer = "Permission_Viewer"
    Manager = "Permission_Manager"
    Admin = "Permission_Admin"

    # ── Сотрудники организации ───────────────────────────────────────────
    Permission_users_see = "Permission_users_see"
    """Видеть список сотрудников компании."""

    Permission_users_create = "Permission_users_create"
    """Добавлять новых сотрудников (email + пароль)."""

    # ── Настройки организации ────────────────────────────────────────────
    Permission_org_settings_see = "Permission_org_settings_see"
    """Открывать страницу настроек компании."""

    Permission_org_settings_edit = "Permission_org_settings_edit"
    """Изменять настройки компании."""
