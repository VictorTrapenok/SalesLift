"""Настройки компании.

Компания приходит сюда из контекста запроса, а не ищется по id из аргументов:
резолвер правит настройки ТОЛЬКО той компании, в которой состоит вошедший
сотрудник. Отдельного «выбери компанию» не существует и не должно появиться.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.models.tenant import Tenant
from saleslift.utils.errors import ValidationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)


class TenantService:
    """Изменение настроек компании."""

    async def update_settings(
        self,
        session: AsyncSession,
        tenant: Tenant,
        name: str,
        country: str | None,
        website: str | None,
        contact_phone: str | None,
    ) -> Tenant:
        """Обновляет название и реквизиты компании.

        Уникальности имени не требуется: единственный идентификатор компании —
        `id`, две «Ромашки» друг другу не мешают.
        """
        clean_name = name.strip()
        if not clean_name:
            raise ValidationError("orgSettings.companyNameRequired", field="name")

        tenant.name = clean_name
        # Пустая строка из формы означает «поле очистили»: колонки nullable,
        # и хранить в них "" вместо NULL — верный способ получить два разных
        # представления одного и того же «не заполнено».
        tenant.country = _clean_optional(country)
        tenant.website = _clean_optional(website)
        tenant.contact_phone = _clean_optional(contact_phone)

        await session.commit()

        log.info("Настройки компании обновлены", tenant_id=str(tenant.id))
        return tenant


def _clean_optional(value: str | None) -> str | None:
    """Приводит необязательное поле формы к `str` или `None`."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


#: Синглтон сервиса — как и остальные сервисы, без DI-контейнера.
tenant_service = TenantService()
