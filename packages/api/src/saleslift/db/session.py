"""Движок SQLAlchemy и выдача сессий.

Сессия НЕ является модульным глобалом (в отличие от соединения Sequelize в
прототипе): `AsyncSession` не безопасна при конкурентном использовании, а один
процесс обслуживает много запросов одновременно. Поэтому сессия создаётся на
запрос и передаётся в сервисы ПЕРВЫМ АРГУМЕНТОМ:

    await auth_service.register(session, input, locale)

Это осознанное отклонение от сигнатуры прототипа. Плюсы: явно, тривиально
тестируется (тест просто передаёт свою сессию) и одинаково работает и в
резолверах, и в фоновых задачах, где никакого запроса нет.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from saleslift.config.settings import settings

# Импорт обязателен: он регистрирует слушателя do_orm_execute, который
# фильтрует мягко удалённые записи. Без него `deleted_at` перестанет
# что-либо значить, причём молча.
from saleslift.db import soft_delete  # noqa: F401

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    # Логи SQL шумны и в dev; при необходимости включается LOG_LEVEL=debug + echo=True.
    echo=False,
    # Проверять соединение перед выдачей из пула: иначе после перезапуска
    # Postgres (или обрыва сети в кластере) приложение отдаёт мёртвые
    # соединения, пока пул сам их не обновит.
    pool_pre_ping=True,
)

session_factory = async_sessionmaker(
    engine,
    # Не сбрасывать атрибуты после commit: иначе обращение к любому полю
    # объекта после коммита вызывает новый SELECT, а в async-коде это ещё и
    # приводит к MissingGreenlet при доступе снаружи await.
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Выдаёт сессию на один запрос. Используется как зависимость FastAPI."""
    async with session_factory() as session:
        yield session
