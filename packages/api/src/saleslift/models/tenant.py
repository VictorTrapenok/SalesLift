"""Организация (тенант) — корневая сущность мультитенантной модели."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from saleslift.db.base import Base, SoftDeleteMixin, TimestampMixin, UuidPkMixin

if TYPE_CHECKING:
    from saleslift.models.user import User


class Tenant(UuidPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Компания-клиент. Всё в системе принадлежит ровно одному тенанту.

    Единственный идентификатор тенанта — `id`. Человекочитаемого slug'а нет
    намеренно: в прототипе он существовал ради поддомена вида
    `<slug>.example.com`, а здесь все кабинеты живут на одном домене без
    поддоменов. Как следствие, названия компаний не обязаны быть уникальными —
    две разные «Ромашки» ничему не мешают. Префиксы ключей в файловом
    хранилище и корреляция в логах строятся по `id`.
    """

    __tablename__ = "tenants"

    #: Название компании. Показывается в интерфейсе, задаётся при регистрации
    #: и меняется в настройках. Уникальности не требует.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Тарифный план. Пока чисто информационное поле: биллинга нет,
    #: ограничений по плану тоже.
    plan: Mapped[str] = mapped_column(String(50), nullable=False, server_default="free")

    #: Отключённой компании запрещён вход всем её сотрудникам (см. auth_service.login).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # ── Реквизиты. Заполняются в настройках компании, все опциональны ─────
    #: Код страны ISO 3166-1 alpha-2 (RU, DE, KZ).
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Связи ────────────────────────────────────────────────────────────
    users: Mapped[list["User"]] = relationship(
        back_populates="tenant",
        # Загрузка только по явному запросу: у компании могут быть сотни
        # сотрудников, и тянуть их при каждом чтении тенанта — верный N+1.
        lazy="raise",
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} name={self.name!r}>"
