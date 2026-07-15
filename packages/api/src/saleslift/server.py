"""Точка входа процесса: `python -m saleslift.server`.

Здесь живёт всё, что требует внешних ресурсов и потому не может быть в `app.py`:
настройка логирования, выбор режима работы (APP_MODE) и запуск uvicorn.

Единственный вход и для разработки, и для production. Запускать uvicorn как CLI
(`uvicorn saleslift.app:create_app`) нельзя: он применяет свой log_config уже
после импорта фабрики и затирает настройку structlog — логи молча возвращаются
к дефолтному формату uvicorn'а. Поэтому hot-reload тоже включается отсюда.
"""

import uvicorn

from saleslift.config.settings import settings
from saleslift.utils.logger import configure_logging, get_logger

log = get_logger(__name__)


def main() -> None:
    """Запускает процесс в режиме, заданном APP_MODE."""
    configure_logging()
    log.info(
        "Запуск SalesLift",
        app_mode=settings.app_mode,
        app_env=settings.app_env,
        port=settings.port,
    )

    if not settings.is_web_mode:
        # Чистый воркер: HTTP не слушаем. Планировщик появится на шаге 9;
        # до тех пор режим worker осознанно завершает процесс, а не делает вид,
        # что работает.
        log.warning("APP_MODE=worker: планировщик фоновых задач ещё не реализован")
        return

    reload_enabled = settings.app_env == "development"

    uvicorn.run(
        # Строка импорта, а не объект: без неё uvicorn не умеет hot-reload.
        "saleslift.app:create_app",
        factory=True,
        # В контейнере слушать нужно все интерфейсы, иначе порт не пробросится наружу.
        host="0.0.0.0",
        port=settings.port,
        reload=reload_enabled,
        reload_dirs=["src"] if reload_enabled else None,
        # None — не трогать logging: конфигурация уже задана configure_logging().
        log_config=None,
        # Access-лог uvicorn'а не структурный; свой появится middleware'ом.
        access_log=False,
    )


if __name__ == "__main__":
    main()
