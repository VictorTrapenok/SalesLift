"""Сотрудник компании."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from saleslift.db.base import Base, SoftDeleteMixin, TimestampMixin, UuidPkMixin

if TYPE_CHECKING:
    from saleslift.models.tenant import Tenant

#: Базовые роли. Маркер роли — первый элемент `users.permissions`, но искать
#: его по индексу нельзя: порядок записей в массиве значения не несёт.
#: Читать права только через `get_effective_permissions()`.
UserRoleName = Literal["admin", "manager", "viewer"]
USER_ROLE_NAMES: tuple[str, ...] = get_args(UserRoleName)

#: Состояние учётной записи.
#:   - `active`    — нормальный рабочий аккаунт, вход разрешён;
#:   - `suspended` — администратор осознанно отключил, вход запрещён.
#:
#: В прототипе были ещё `invited`/`pending`/`rejected`: они обслуживали флоу
#: приглашений по ссылке и заявок на вступление. Здесь администратор задаёт
#: пароль сотруднику напрямую, поэтому эти состояния не нужны. Набор
#: расширяется миграцией, когда появятся приглашения.
UserStatus = Literal["active", "suspended"]
USER_STATUSES: tuple[str, ...] = get_args(UserStatus)


class User(UuidPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Сотрудник компании.

    E-mail ГЛОБАЛЬНО уникален (частичный индекс `uq_users_email`). Это прямое
    следствие отказа от поддоменов: форма логина — только email и пароль, а
    компания выводится из найденной строки пользователя. Цена решения: один
    e-mail не может работать в двух компаниях одновременно.
    """

    __tablename__ = "users"
    __table_args__ = (
        # Глобальная уникальность e-mail. Индекс ЧАСТИЧНЫЙ (только живые строки),
        # поэтому адрес уволенного сотрудника можно переиспользовать: его строка
        # остаётся с проставленным deleted_at и уникальности не мешает.
        Index(
            "uq_users_email",
            "email",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Выборка сотрудников компании — самый частый запрос в кабинете.
        Index(
            "ix_users_tenant_id",
            "tenant_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # Имя без префикса таблицы: его добавит шаблон `ck_%(table_name)s_...`
        # из naming_convention, иначе получится `ck_users_users_status`.
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in USER_STATUSES)})",
            name="status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Хранится нормализованным: обрезанный, в нижнем регистре. Нормализацию
    #: обеспечивает валидатор ниже + сервисный слой перед каждым поиском.
    #: От этого зависит уникальный индекс: он по обычной колонке, а не по
    #: lower(email), поэтому дисциплина записи — обязательна.
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    #: NULL допустим: будущий флоу приглашений создаёт строку до того, как
    #: сотрудник задал пароль. Вход при NULL невозможен (см. auth_service.login).
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    #: Массив прав: маркер роли (`admin`/`manager`/`viewer`) плюс опционально
    #: значения `UserPermissions`, точечно расширяющие роль. Порядок значения
    #: не несёт — читать через `get_effective_permissions()`.
    permissions: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        server_default='["admin"]',
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="active",
    )

    #: Предпочитаемый язык (ISO 639-1). Определяет язык серверных сообщений
    #: об ошибках; интерфейс берёт язык из своего localStorage.
    locale: Mapped[str] = mapped_column(String(2), nullable=False, server_default="en")

    #: Краткое описание сотрудника. Редактируется в профиле.
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Чисто информационное поле: никакой логики на нём строить нельзя.
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Связи ────────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship(back_populates="users", lazy="raise")

    @validates("email")
    def _normalize_email(self, _key: str, value: str) -> str:
        """Нормализует e-mail при любом присваивании.

        Вторая линия защиты после сервисного слоя: уникальный индекс построен
        по обычной колонке, поэтому «Ivan@Mail.RU» и «ivan@mail.ru» без
        нормализации оказались бы разными адресами и оба прошли бы проверку.
        """
        return value.strip().lower()

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} tenant_id={self.tenant_id}>"
