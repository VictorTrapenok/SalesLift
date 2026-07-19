"""Резолверы настроек компании.

Компания берётся из контекста запроса, а не из аргументов: сотрудник правит
настройки только своей компании. Бизнес-логика — в
`services/tenants/tenant_service.py`.
"""

import strawberry
from strawberry.types import Info

from saleslift.graphql.context import Context
from saleslift.graphql.types.tenant import Tenant
from saleslift.services.permissions import UserPermissions
from saleslift.services.tenants import tenant_service as tenant_module
from saleslift.services.users.user_roles_permission import require_permission


@strawberry.input(description="Настройки компании")
class UpdateOrgSettingsInput:
    """Поля формы настроек. Кроме названия, всё опционально."""

    name: str
    #: Код страны ISO 3166-1 alpha-2 (RU, DE, KZ).
    country: str | None = None
    website: str | None = None
    contact_phone: str | None = None


@strawberry.type
class OrgSettingsQuery:
    """Чтение настроек компании."""

    @strawberry.field(description="Настройки компании текущего сотрудника")
    async def resolver_org_settings_get(self, info: Info[Context, None]) -> Tenant:
        """Возвращает компанию вошедшего сотрудника.

        Отдельный резолвер, хотя компания доступна и через `resolverAuthMe`:
        страница настроек гейтится правом `Permission_org_settings_see`, и
        право должно проверяться там же, где отдаются данные.
        """
        auth = require_permission(info.context, UserPermissions.Permission_org_settings_see)
        return Tenant.from_model(auth.tenant)


@strawberry.type
class OrgSettingsMutation:
    """Изменение настроек компании."""

    @strawberry.mutation(description="Сохранить настройки компании")
    async def resolver_org_settings_update(self, info: Info[Context, None], input: UpdateOrgSettingsInput) -> Tenant:
        """Сохраняет название и реквизиты компании."""
        auth = require_permission(info.context, UserPermissions.Permission_org_settings_edit)
        tenant = await tenant_module.tenant_service.update_settings(
            info.context.session,
            auth.tenant,
            name=input.name,
            country=input.country,
            website=input.website,
            contact_phone=input.contact_phone,
        )
        return Tenant.from_model(tenant)
