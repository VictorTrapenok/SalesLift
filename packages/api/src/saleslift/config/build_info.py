"""Информация о сборке образа.

Значения запекаются в образ на этапе сборки (ARG → ENV в Dockerfile) и
отдаются в `/api/v1/health`. Это то, что позволяет посмотреть на работающий
под и однозначно сказать, какой коммит в нём крутится.

Вне собранного образа (локальная разработка) значения остаются дефолтными.
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildInfo:
    """Метаданные сборки образа."""

    branch: str
    pipeline_id: str
    build_id: str


build_info = BuildInfo(
    branch=os.environ.get("BUILD_BRANCH", "local"),
    pipeline_id=os.environ.get("BUILD_PIPELINE_ID", "0"),
    build_id=os.environ.get("BUILD_ID", "0"),
)
