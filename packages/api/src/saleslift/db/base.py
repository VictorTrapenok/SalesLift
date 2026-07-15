"""Базовый класс ORM-моделей и переиспользуемые миксины.

Соглашения, общие для всех таблиц проекта:
  - первичный ключ — UUIDv4, генерируется базой (`UuidPkMixin`);
  - у каждой таблицы есть `created_at`/`updated_at` (`TimestampMixin`);
  - удаление мягкое, через `deleted_at` (`SoftDeleteMixin` + `db/soft_delete.py`).

Имена колонок отдельно настраивать не нужно: атрибуты Python и так snake_case,
поэтому аналог `underscored: true` из Sequelize здесь просто не требуется.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, Uuid, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей проекта."""

    # Явные шаблоны имён: без них Alembic генерирует для ограничений случайные
    # имена, и миграция, снимающая ограничение, не может его найти по имени.
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class UuidPkMixin:
    """Первичный ключ UUIDv4, генерируемый базой."""

    #: Генерация на стороне БД (`gen_random_uuid()`, встроен в PostgreSQL с 13
    #: версии — расширение pgcrypto ставить не нужно). Так строка получает id
    #: даже если её вставили в обход ORM.
    #:
    #: sort_order=-100 — чтобы в DDL и в выводе `\d` id шёл первой колонкой:
    #: без него колонки миксинов оказываются в конце таблицы.
    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        sort_order=-100,
    )


class TimestampMixin:
    """Отметки времени создания и последнего изменения.

    sort_order=100 — служебные колонки идут в конце таблицы, после доменных.
    """

    #: Проставляется базой при вставке.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        sort_order=100,
    )

    #: Обновляется на каждом UPDATE. `onupdate` — на стороне Python: серверный
    #: аналог потребовал бы триггера, а он невидим в коде моделей и потому
    #: неизбежно рассинхронится с ними.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        sort_order=101,
    )


class SoftDeleteMixin:
    """Мягкое удаление — аналог `paranoid: true` из Sequelize.

    Сам по себе миксин только добавляет колонку. Фильтрация удалённых записей
    из всех SELECT'ов включается глобальным слушателем в `db/soft_delete.py`.
    """

    #: NULL — запись жива. Дата — момент удаления.
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        sort_order=102,
    )
