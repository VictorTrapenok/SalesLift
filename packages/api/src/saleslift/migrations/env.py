"""Окружение Alembic.

Два отличия от шаблона по умолчанию:

1. URL подключения берётся из `settings`, а НЕ из `alembic.ini`. Конфигурация
   БД должна быть в одном месте: иначе рано или поздно приложение и миграции
   поедут в разные базы.
2. Синхронный драйвер не нужен: async-движок отдаёт соединение в
   `connection.run_sync()`, и Alembic работает поверх него. Поэтому в
   зависимостях нет psycopg2 — только asyncpg.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from saleslift.config.settings import settings

# Импорт реестра моделей обязателен: без него Base.metadata пуста и
# autogenerate решит, что все таблицы надо удалить.
from saleslift.models import Base

config = context.config

# Подставляем реальный URL поверх плейсхолдера из alembic.ini.
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерирует SQL без подключения к базе (`alembic upgrade --sql`)."""
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Выполняет миграции на уже открытом соединении."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # Замечать смену типа и серверного дефолта: без этого расхождение
        # моделей со схемой не попадёт в autogenerate и разъедется молча.
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Открывает async-соединение и прогоняет миграции через run_sync."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Точка входа онлайн-режима.

    Если соединение передано снаружи через `config.attributes["connection"]`
    (так делает conftest.py тестов), работаем на нём. Иначе — открываем своё.
    Без этой ветки прогон миграций из кода создавал бы второе подключение к той
    же базе параллельно с уже открытым, что приводит к взаимной блокировке на
    DDL-локах.
    """
    external_connection: Connection | None = config.attributes.get("connection")
    if external_connection is not None:
        do_run_migrations(external_connection)
        return

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
