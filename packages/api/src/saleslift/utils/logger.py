"""Структурное логирование через structlog.

В development логи человекочитаемые и цветные, в production и test — JSON:
машинный формат нужен и для сбора логов в кластере, и для CI, где файл с
логами прикладывается артефактом к прогону.

Правило проекта: каждый `except` логирует. Пустые `except: pass` запрещены —
если ошибку действительно можно проигнорировать, комментарием поясняется, почему.
"""

import logging
import sys
from typing import Any

import structlog

from saleslift.config.settings import settings


def _build_processors(*, json_output: bool) -> list[Any]:
    """Собирает цепочку процессоров structlog."""
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        # Разворачивает exc_info в текст трейсбека — без него logger.exception()
        # в JSON-режиме потерял бы сам стектрейс.
        structlog.processors.format_exc_info,
    ]
    renderer: Any = structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer()
    return [*shared, renderer]


def configure_logging() -> None:
    """Настраивает structlog и стандартный logging. Вызывается один раз на старте процесса."""
    json_output = settings.app_env != "development"
    level = getattr(logging, settings.log_level.upper())

    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.log_file_path:
        # Файловый сток нужен CI: файл монтируется наружу и прикладывается
        # артефактом к прогону. Если путь недоступен — падаем громко, а не
        # тихо теряем логи: молча потерянные логи хуже, чем упавший старт.
        handlers.append(logging.FileHandler(settings.log_file_path, encoding="utf-8"))

    logging.basicConfig(format="%(message)s", level=level, handlers=handlers, force=True)

    structlog.configure(
        processors=_build_processors(json_output=json_output),
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Возвращает логгер. Имя обычно `__name__` вызывающего модуля."""
    logger: structlog.stdlib.BoundLogger = structlog.get_logger(name)
    return logger
