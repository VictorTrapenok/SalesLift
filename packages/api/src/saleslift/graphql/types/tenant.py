"""GraphQL-тип компании."""

import uuid

import strawberry

from saleslift.models.tenant import Tenant as TenantModel


@strawberry.type(description="Компания-клиент")
class Tenant:
    """Компания в терминах API.

    Slug'а нет: единственный идентификатор компании — `id`. Названия компаний
    не уникальны.
    """

    id: uuid.UUID
    name: str
    plan: str
    country: str | None
    website: str | None
    contact_phone: str | None

    @classmethod
    def from_model(cls, model: TenantModel) -> "Tenant":
        """Собирает GraphQL-тип из ORM-модели."""
        return cls(
            id=model.id,
            name=model.name,
            plan=model.plan,
            country=model.country,
            website=model.website,
            contact_phone=model.contact_phone,
        )
