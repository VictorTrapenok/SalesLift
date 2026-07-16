"""Фикстуры интеграционных тестов: реальная PostgreSQL в Docker, без моков.

Файл лежит в `tests/integration/`, а НЕ в `tests/`: фикстура `clean_db` —
autouse, и в корневом conftest она заставляла бы юнит-тесты (которым база не
нужна вовсе) подключаться к PostgreSQL. Граница «нужна ли БД» проходит по
каталогу, и conftest должен лежать по ту же сторону.

Окружение подгружается снаружи — `uv run --env-file .env.test pytest`
(см. Makefile). Поэтому в этом файле нет возни с ручным чтением .env до
импортов: все импорты остаются в начале файла, как требует стиль проекта.

Модель изоляции повторяет прототип:

  - миграции прогоняются ОДИН раз за сессию;
  - TRUNCATE — один раз перед каждым тестовым МОДУЛЕМ, а не перед каждым тестом;
  - тенант создаётся на каждый тест.

Комбинация «TRUNCATE на модуль + тенант на тест» и делает осмысленными проверки
изоляции: в базе есть реальные чужие данные, которые запрос может утечь.

НЕ ДОБАВЛЯЙТЕ pytest-xdist. Все интеграционные тесты делят одну тестовую базу,
и параллельный прогон вернёт ровно те дедлоки на TRUNCATE и гонки миграций,
которые описаны в TESTING.md.
"""

import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from saleslift.config.settings import settings
from saleslift.models import Tenant, User

#: Таблицы для очистки. Порядок не важен — CASCADE разберётся со связями,
#: но список должен быть полным: забытая таблица протечёт данными между тестами.
_TABLES_TO_TRUNCATE = ("background_tasks", "users", "tenants")


def _guard_test_environment() -> None:
    """Не даёт прогону тестов уничтожить рабочую базу.

    Тесты делают TRUNCATE. Если pytest запустили без `--env-file .env.test`,
    настройки укажут на базу разработки на порту 5432 — и данные, с которыми вы
    работаете руками, будут стёрты. Проверка стоит здесь, а не в документации,
    потому что цена ошибки высока, а стоимость проверки нулевая.
    """
    if settings.app_env != "test":
        pytest.exit(
            f"APP_ENV={settings.app_env!r}, ожидалось 'test'.\n"
            f"Тесты делают TRUNCATE и должны работать только с тестовой базой.\n"
            f"Запускайте через `make test-integration` либо "
            f"`uv run --env-file .env.test pytest`.",
            returncode=1,
        )


def _run_alembic_upgrade(connection: Connection) -> None:
    """Накатывает все миграции на переданное соединение."""
    # tests/integration/conftest.py → packages/api/alembic.ini
    alembic_cfg = Config(str(Path(__file__).parents[2] / "alembic.ini"))
    # Отдаём Alembic уже открытое соединение: иначе env.py откроет своё,
    # и мы получим два подключения к одной базе внутри одного теста.
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
async def db_engine() -> AsyncGenerator[AsyncEngine]:
    """Движок тестовой БД со всеми накатанными миграциями.

    Создаётся один раз на прогон. Закрывать его между файлами не нужно (в
    отличие от прототипа, где `sequelize.close()` в teardown вынуждал давать
    каждому файлу свой процесс): pytest однопоточен, движок живёт весь прогон.

    NullPool — соединения не переиспользуются между тестами, что исключает
    залипание состояния сессии.
    """
    _guard_test_environment()

    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(_run_alembic_upgrade)

    yield engine

    await engine.dispose()


@pytest.fixture(scope="module", autouse=True)
async def clean_db(db_engine: AsyncEngine) -> None:
    """Очищает базу перед каждым тестовым модулем.

    ОДНИМ statement'ом TRUNCATE ... CASCADE, а не циклом по таблицам:
    PostgreSQL берёт AccessExclusive-локи на все перечисленные таблицы
    атомарно, поэтому конкурентные вызовы не могут заблокировать друг друга.
    Сейчас, при однопоточном pytest, гонок нет — но так просто быстрее (один
    запрос вместо N), а защита от дедлоков уже на месте, если параллелизм
    когда-нибудь появится. В прототипе до перехода на единый statement тесты
    падали с `deadlock detected`.

    Перед модулем, а не перед каждым тестом: тесты внутри модуля опираются на
    данные, созданные ранее в этом же модуле.
    """
    tables = ", ".join(f'"{t}"' for t in _TABLES_TO_TRUNCATE)
    async with db_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {tables} CASCADE"))


@pytest.fixture
async def session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Сессия на один тест.

    Тест НЕ оборачивается в откатываемую транзакцию: границами транзакций
    управляет сервисный слой, и подменять их — значит проверять не тот код,
    который поедет в production. Данные реально коммитятся, чистит их
    `clean_db`.
    """
    async with async_sessionmaker(db_engine, expire_on_commit=False)() as s:
        yield s


@pytest.fixture
async def tenant(session: AsyncSession) -> Tenant:
    """Компания для теста.

    Уникальных полей у тенанта нет (slug'а не существует), поэтому никаких
    суффиксов не нужно: каждый вызов просто создаёт новую строку со своим id.
    """
    tenant = Tenant(name="Тестовая компания")
    session.add(tenant)
    await session.commit()
    return tenant


@pytest.fixture
async def other_tenant(session: AsyncSession) -> Tenant:
    """Вторая компания — для проверок изоляции.

    У КАЖДОГО tenant-scoped сервиса должен быть тест «не видит данные чужого
    тенанта», использующий эту фикстуру. Мультитенантность здесь держится на
    явном `.where(tenant_id == ...)` в каждом запросе, а не на магии ORM, —
    значит, единственная её гарантия это тесты.
    """
    tenant = Tenant(name="Чужая компания")
    session.add(tenant)
    await session.commit()
    return tenant


@pytest.fixture
async def admin_user(session: AsyncSession, tenant: Tenant) -> User:
    """Активный администратор компании из фикстуры `tenant`.

    E-mail с uuid-суффиксом: он глобально уникален (частичный индекс
    `uq_users_email`), а внутри модуля данные от предыдущих тестов ещё живы,
    поэтому фиксированный адрес привёл бы к нарушению уникальности.
    """
    user = User(
        tenant_id=tenant.id,
        name="Администратор",
        email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
        permissions=["admin"],
        status="active",
        locale="ru",
    )
    session.add(user)
    await session.commit()
    return user
