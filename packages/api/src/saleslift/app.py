"""Фабрика ASGI-приложения.

Отдельная фабрика, а не готовый модульный объект: тесты собирают приложение без
подключения к БД и без запуска планировщика. Всё, что требует внешних ресурсов,
живёт в `server.py` — здесь только сборка роутов.
"""

from fastapi import FastAPI

from saleslift import __version__
from saleslift.graphql.router import GRAPHQL_PATH, create_graphql_router
from saleslift.routes import health
from saleslift.utils.logger import configure_logging


def create_app() -> FastAPI:
    """Собирает FastAPI-приложение со всеми роутами."""
    # Настраиваем логирование здесь, а не только в server.py: при hot-reload
    # (`make dev`) uvicorn импортирует эту фабрику напрямую, минуя server.py,
    # и без этого вызова логи шли бы дефолтным форматом uvicorn'а.
    # Вызов идемпотентен, повторный из server.py безвреден.
    configure_logging()

    app = FastAPI(
        title="SalesLift API",
        version=__version__,
        # Схема API публикуется через GraphQL; автодоки FastAPI описывали бы
        # только health и потому вводили бы в заблуждение.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.include_router(health.router)
    app.include_router(create_graphql_router(), prefix=GRAPHQL_PATH)

    return app
