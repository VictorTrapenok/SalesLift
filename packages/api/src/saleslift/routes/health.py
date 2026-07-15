"""REST-эндпоинт проверки живости.

Используется readiness/liveness-пробами k8s, healthcheck'ом docker compose и
CI (который ждёт готовности бэкенда перед прогоном e2e). Намеренно REST, а не
GraphQL: пробы должны быть тривиальными GET'ами без тела запроса.

Намеренно НЕ ходит в базу: проба живости отвечает на вопрос «процесс жив и
обслуживает HTTP», а не «жива ли вся система». Если завязать её на БД, то
кратковременная недоступность базы приведёт к перезапуску подов, которые на
самом деле исправны, — и вместо одной проблемы станет две.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from saleslift import __version__
from saleslift.config.build_info import build_info

router = APIRouter(tags=["health"])


class BuildInfoResponse(BaseModel):
    """Информация о сборке образа."""

    branch: str
    pipeline_id: str
    build_id: str


class HealthResponse(BaseModel):
    """Ответ проверки живости."""

    status: str
    version: str
    build: BuildInfoResponse


@router.get("/api/v1/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Возвращает статус процесса и информацию о сборке."""
    return HealthResponse(
        status="ok",
        version=__version__,
        build=BuildInfoResponse(
            branch=build_info.branch,
            pipeline_id=build_info.pipeline_id,
            build_id=build_info.build_id,
        ),
    )
