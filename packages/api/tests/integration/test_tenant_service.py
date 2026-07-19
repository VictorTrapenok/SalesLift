"""Интеграционные проверки настроек компании."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.models import Tenant
from saleslift.services.tenants.tenant_service import tenant_service
from saleslift.utils.errors import ValidationError


class TestUpdateSettings:
    """Изменение настроек компании."""

    async def test_сохраняет_название_и_реквизиты(self, session: AsyncSession, tenant: Tenant) -> None:
        updated = await tenant_service.update_settings(
            session,
            tenant,
            name="  ООО Ромашка  ",
            country="RU",
            website="https://example.com",
            contact_phone="+7 900 000-00-00",
        )

        assert updated.name == "ООО Ромашка"
        assert updated.country == "RU"
        assert updated.website == "https://example.com"
        assert updated.contact_phone == "+7 900 000-00-00"

    async def test_пустые_реквизиты_становятся_null(self, session: AsyncSession, tenant: Tenant) -> None:
        """Иначе «не заполнено» имело бы два представления: NULL и пустую строку."""
        await tenant_service.update_settings(session, tenant, "Ромашка", "RU", "https://example.com", "+79000000000")

        updated = await tenant_service.update_settings(session, tenant, "Ромашка", "", "   ", None)

        assert updated.country is None
        assert updated.website is None
        assert updated.contact_phone is None

    async def test_пустое_название_отвергается(self, session: AsyncSession, tenant: Tenant) -> None:
        with pytest.raises(ValidationError) as err:
            await tenant_service.update_settings(session, tenant, "   ", None, None, None)

        assert err.value.i18n_key == "orgSettings.companyNameRequired"
        assert err.value.field == "name"

    async def test_одинаковые_названия_компаний_разрешены(
        self,
        session: AsyncSession,
        tenant: Tenant,
        other_tenant: Tenant,
    ) -> None:
        """Единственный идентификатор компании — id: две «Ромашки» друг другу не мешают."""
        await tenant_service.update_settings(session, other_tenant, "Ромашка", None, None, None)
        await tenant_service.update_settings(session, tenant, "Ромашка", None, None, None)

        assert tenant.name == other_tenant.name
        assert tenant.id != other_tenant.id
