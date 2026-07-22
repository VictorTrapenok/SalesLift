# Единая точка входа для всех команд проекта.
# `make` без аргументов покажет список доступных целей с описанием.

.DEFAULT_GOAL := help
SHELL := /bin/bash

API := packages/api
WEB := packages/web
UV  := uv --project $(API)
# Порт для `make dev`. Переопределяется, если 8000 занят: `make dev PORT=8081`.
PORT ?= 8000

.PHONY: help up down logs reset dev-api dev-web db-migrate schema codegen test \
        test-integration test-db-start test-db-stop lint format typecheck \
        protect-main protect-main-show

help: ## Показать список команд
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Запуск ────────────────────────────────────────────────────────────────

up: ## Запустить SalesLift → http://localhost:8000
	docker compose up -d --wait
	@echo ""
	@echo "  ✅ SalesLift готов: http://localhost:$(PORT)"
	@echo ""

down: ## Остановить SalesLift
	docker compose down

logs: ## Смотреть логи приложения
	docker compose logs -f app

reset: ## Остановить и УДАЛИТЬ все данные (чистый старт)
	docker compose down -v

dev-api: ## Разработка: БД в Docker + API с hot-reload (порт: make dev-api PORT=8081)
	docker compose up -d db --wait
	# Через server.py, а не uvicorn CLI: CLI затирает настройку structlog своим log_config.
	cd $(API) && DB_HOST=localhost PORT=$(PORT) uv run python -m saleslift.server

dev-web: ## Разработка: фронтенд с hot-reload на :5173 (проксирует /api на $(PORT))
	cd $(WEB) && API_PORT=$(PORT) npm run dev

db-migrate: ## Накатить миграции на БД разработки
	docker compose up -d db --wait
	cd $(API) && DB_HOST=localhost uv run alembic upgrade head

# ── Кодогенерация ─────────────────────────────────────────────────────────

schema: ## Экспорт GraphQL SDL → packages/api/schema.graphql
	$(UV) run strawberry export-schema saleslift.graphql.schema:schema > $(API)/schema.graphql
	@echo "  ✅ $(API)/schema.graphql обновлён"

codegen: schema ## schema + генерация TypeScript-типов фронтенда
	npm --prefix $(WEB) run codegen

# ── Тесты ─────────────────────────────────────────────────────────────────

test: ## Unit-тесты (без БД)
	cd $(API) && uv run --env-file .env.test pytest tests/unit

test-db-start: ## Поднять тестовую PostgreSQL (порт 5433)
	bash $(API)/scripts/test-db.sh start

test-db-stop: ## Остановить тестовую PostgreSQL
	bash $(API)/scripts/test-db.sh stop

test-integration: ## Интеграционные тесты (реальная PostgreSQL в Docker)
	# --env-file .env.test обязателен: он уводит тесты на изолированную БД (порт
	# 5433). Без него conftest откажется работать — тесты делают TRUNCATE.
	# Контейнер гасим в любом случае, но код возврата pytest сохраняем.
	@bash $(API)/scripts/test-db.sh start
	@cd $(API) && uv run --env-file .env.test pytest tests; CODE=$$?; \
		bash scripts/test-db.sh stop; \
		exit $$CODE

# ── Качество кода ─────────────────────────────────────────────────────────

lint: ## ruff check + eslint
	$(UV) run ruff check $(API)
	$(UV) run ruff format --check $(API)
	@[ -d $(WEB)/node_modules ] && npm --prefix $(WEB) run lint || echo "  ⏭  фронтенд ещё не установлен, пропускаю eslint"

format: ## ruff format + prettier
	$(UV) run ruff format $(API)
	$(UV) run ruff check --fix $(API)
	@[ -d $(WEB)/node_modules ] && npm --prefix $(WEB) run format || echo "  ⏭  фронтенд ещё не установлен, пропускаю prettier"

typecheck: ## mypy --strict + tsc --noEmit
	# cd в пакет: mypy резолвит `files` из pyproject.toml относительно CWD, а не конфига.
	cd $(API) && uv run mypy
	@[ -d $(WEB)/node_modules ] && npm --prefix $(WEB) run typecheck || echo "  ⏭  фронтенд ещё не установлен, пропускаю tsc"

# ── Репозиторий ───────────────────────────────────────────────────────────

protect-main: ## Применить защиту ветки main (.github/rulesets/main.json)
	bash scripts/apply-ruleset.sh

protect-main-show: ## Показать, какая защита ветки main сейчас включена
	bash scripts/apply-ruleset.sh --show
