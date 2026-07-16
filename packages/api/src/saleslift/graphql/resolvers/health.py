"""Health-резолвер: информация о сборке через GraphQL.

REST-эндпоинт `/api/v1/health` остаётся для проб k8s и docker (им нужен
простой GET). Этот резолвер — для интерфейса: показать в футере, какая версия
крутится, не заводя отдельный HTTP-клиент.
"""

import strawberry

from saleslift import __version__
from saleslift.config.build_info import build_info


@strawberry.type(description="Информация о сборке образа")
class BuildInfo:
    """Метаданные сборки — запекаются в образ на этапе сборки."""

    branch: str
    pipeline_id: str
    build_id: str


@strawberry.type(description="Состояние сервиса")
class HealthStatus:
    """Статус процесса и версия."""

    status: str
    version: str
    build: BuildInfo


@strawberry.type
class HealthQuery:
    """Запрос состояния сервиса."""

    @strawberry.field(description="Состояние сервиса и информация о сборке")
    async def health(self) -> HealthStatus:
        """Возвращает статус и версию. Публичный запрос, авторизации не требует."""
        return HealthStatus(
            status="ok",
            version=__version__,
            build=BuildInfo(
                branch=build_info.branch,
                pipeline_id=build_info.pipeline_id,
                build_id=build_info.build_id,
            ),
        )
