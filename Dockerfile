# syntax=docker/dockerfile:1.7
#
# Один образ содержит бэкенд и собранную SPA: бэкенд раздаёт фронтенд сам.
# Тот же образ работает воркером — режим переключается переменной APP_MODE.

# ── Стейдж 1: бэкенд + экспорт GraphQL-схемы ──────────────────────────────
# Бэкенд собирается ПЕРВЫМ, потому что фронтенду нужен его schema.graphql:
# кодогенерация типов читает SDL-файл и не требует запущенного сервера.
#
# ВНИМАНИЕ: тег ОБЯЗАН совпадать с packages/api/.python-version (сейчас 3.13),
# и менять их можно только вместе. Ниже uv собирает venv по .python-version.
# Если версия в теге другая, uv не возьмёт интерпретатор базового образа, а
# скачает свой — в /root/.local/share/uv/python/. Venv будет ссылаться туда,
# а в runtime-стейдж копируется только сам venv, и /root там недоступен
# пользователю app (права 700). Итог: symlink не резолвится, любой скрипт из
# venv падает с «Permission denied» и кодом 126 — при том что сборка образа
# проходит успешно, и ломается только запуск. Так уже ловили миграции (PR #3).
FROM python:3.13-slim AS api-builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /bin/uv

WORKDIR /app/packages/api
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Сначала только манифесты: слой с зависимостями кэшируется отдельно от кода,
# поэтому правка исходников не приводит к переустановке пакетов.
COPY packages/api/pyproject.toml packages/api/uv.lock packages/api/.python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

COPY packages/api/src ./src
COPY packages/api/README.md* ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# APP_ENV=development — экспорт схемы не должен требовать прод-секретов.
# Импорт схемы тянет settings, и в production-режиме те откажутся стартовать с
# дефолтными JWT_SECRET и паролем БД, которых в билдере нет и быть не должно.
ENV APP_ENV=development
RUN uv run strawberry export-schema saleslift.graphql.schema:schema > /app/packages/api/schema.graphql

# ── Стейдж 2: фронтенд (codegen → сборка) ─────────────────────────────────
FROM node:26-alpine AS web-builder

WORKDIR /app/packages/web

COPY packages/web/package.json packages/web/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm,sharing=locked \
    npm ci --no-audit --no-fund

COPY packages/web ./

# Схема из стейджа бэкенда. Путь ОБЯЗАН совпадать с тем, что указан в
# codegen.ts (../api/schema.graphql), иначе кодогенерация не найдёт файл.
COPY --from=api-builder /app/packages/api/schema.graphql /app/packages/api/schema.graphql

ARG BUILD_BRANCH=unknown
ARG BUILD_PIPELINE_ID=0
ARG BUILD_ID=0
ENV VITE_BUILD_BRANCH=${BUILD_BRANCH} \
    VITE_BUILD_PIPELINE_ID=${BUILD_PIPELINE_ID} \
    VITE_BUILD_ID=${BUILD_ID}

# Кодогенерация ДО сборки — и это не порядок ради порядка: если фронтенд
# запрашивает поле, которого нет в схеме, codegen падает здесь, и образ просто
# не собирается. Рассинхрон бэкенда и фронтенда физически не доедет до registry.
RUN npm run codegen
RUN npm run build

# ── Стейдж 3: runtime ─────────────────────────────────────────────────────
# slim, а не alpine: musl ломает manylinux-колёса asyncpg и bcrypt и заставляет
# собирать их из исходников. Slim с колёсами и меньше, и быстрее.
FROM python:3.13-slim AS runtime

ARG BUILD_BRANCH=unknown
ARG BUILD_PIPELINE_ID=0
ARG BUILD_ID=0
ENV BUILD_BRANCH=${BUILD_BRANCH} \
    BUILD_PIPELINE_ID=${BUILD_PIPELINE_ID} \
    BUILD_ID=${BUILD_ID}

ENV APP_ENV=production \
    PATH="/app/packages/api/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Не из-под root: процессу в контейнере права суперпользователя не нужны.
RUN useradd --create-home --uid 10001 app

WORKDIR /app/packages/api

COPY --from=api-builder --chown=app:app /app/packages/api/.venv ./.venv
COPY --from=api-builder --chown=app:app /app/packages/api/src ./src
COPY --chown=app:app packages/api/alembic.ini ./
COPY --chown=app:app packages/api/docker-entrypoint.sh ./

# Собранная SPA. Путь совпадает с SPA_DIST_DIR в saleslift/static.py.
COPY --from=web-builder --chown=app:app /app/packages/web/dist /app/packages/web/dist

RUN chmod +x docker-entrypoint.sh

USER app
EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "saleslift.server"]
