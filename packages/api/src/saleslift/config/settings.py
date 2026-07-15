"""Конфигурация приложения из переменных окружения.

Все настройки валидируются на старте процесса: при некорректном окружении
приложение падает сразу с понятным сообщением, а не через десять минут работы
на первом обращении к незаданной переменной.

Важно: этот модуль НЕ открывает соединений и не делает сетевых вызовов на
импорте — только читает и валидирует окружение. От этого зависит экспорт
GraphQL-схемы в Docker-сборке, где ни БД, ни секретов нет
(см. tests/unit/test_schema_export.py и стейдж api-builder в Dockerfile).
"""

import sys
from typing import Literal

from pydantic import Field, PostgresDsn, ValidationError, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Режим запуска процесса.
#   - `web`    — обслуживает HTTP (GraphQL + REST + раздача SPA), джобы не гоняет;
#   - `worker` — крутит планировщик фоновых задач, HTTP не слушает;
#   - `all`    — и то, и другое в одном процессе. Дефолт для локальной разработки
#                и для docker compose; в k8s режимы разнесены по разным подам.
AppMode = Literal["web", "worker", "all"]

AppEnv = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Настройки приложения. Читаются из окружения один раз при импорте модуля."""

    model_config = SettingsConfigDict(
        env_file=None,  # .env подключается снаружи: docker compose env_file / uv run --env-file
        extra="ignore",
        case_sensitive=False,
    )

    # ── Общие ─────────────────────────────────────────────────────────────
    app_env: AppEnv = "development"
    app_mode: AppMode = "all"
    port: int = Field(default=8000, gt=0, lt=65536)

    # ── База данных ───────────────────────────────────────────────────────
    db_host: str = "localhost"
    db_port: int = Field(default=5432, gt=0, lt=65536)
    db_name: str = "saleslift"
    db_user: str = "saleslift"
    db_password: str = "saleslift"

    # ── Логирование ───────────────────────────────────────────────────────
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    # Путь к файлу для JSON-логов. Задаётся в CI: файл монтируется наружу и
    # прикладывается артефактом к прогону — именно это делает красный билд
    # отлаживаемым. Пусто — пишем только в stdout.
    log_file_path: str | None = None

    # ── Аутентификация ────────────────────────────────────────────────────
    # ВАЖНО: дефолт годится ТОЛЬКО для разработки. В production пустой или
    # дефолтный секрет отвергается валидатором ниже — см. _check_production_secrets.
    jwt_secret: str = "dev-only-secret-change-me-in-production-min-32"
    jwt_expires_in: str = "7d"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """URL подключения для SQLAlchemy (async-драйвер asyncpg)."""
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port,
                path=self.db_name,
            )
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_web_mode(self) -> bool:
        """Должен ли этот процесс обслуживать HTTP."""
        return self.app_mode in ("web", "all")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_worker_mode(self) -> bool:
        """Должен ли этот процесс гонять фоновые задачи."""
        return self.app_mode in ("worker", "all")


# Дефолтные значения секретов. Пригодны для разработки, недопустимы в production:
# сверяемся с этим списком, чтобы «забыл задать переменную» не уехало в прод молча.
_DEV_DEFAULT_SECRETS = {
    "jwt_secret": "dev-only-secret-change-me-in-production-min-32",
    "db_password": "saleslift",
}

_MIN_JWT_SECRET_LENGTH = 32


def _check_production_secrets(settings: Settings) -> list[str]:
    """Проверяет, что в production не остались dev-дефолты секретов.

    Возвращает список сообщений об ошибках; пустой список — всё в порядке.
    В development и test дефолты разрешены — в этом и смысл: `make dev` и
    `make test` должны работать без единой заданной переменной.
    """
    if settings.app_env != "production":
        return []

    errors: list[str] = []
    for field_name, dev_default in _DEV_DEFAULT_SECRETS.items():
        if getattr(settings, field_name) == dev_default:
            errors.append(f"{field_name.upper()}: в production нельзя оставлять значение по умолчанию")

    if len(settings.jwt_secret) < _MIN_JWT_SECRET_LENGTH:
        errors.append(f"JWT_SECRET: минимум {_MIN_JWT_SECRET_LENGTH} символов, получено {len(settings.jwt_secret)}")

    return errors


def _load_settings() -> Settings:
    """Загружает и валидирует настройки; при ошибке завершает процесс.

    Падаем через sys.exit(1), а не исключением: некорректное окружение — это
    ошибка конфигурации, а не рантайма, и стектрейс pydantic'а здесь только
    мешает читать список того, что именно не задано.
    """
    try:
        settings = Settings()
    except ValidationError as err:
        print(f"❌ Некорректные переменные окружения:\n{err}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    if production_errors := _check_production_secrets(settings):
        details = "\n".join(f"  - {e}" for e in production_errors)
        print(f"❌ Некорректная конфигурация production:\n{details}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    return settings


settings = _load_settings()
