# Единая точка входа для всех команд проекта.
# `make` без аргументов покажет список доступных целей с описанием.

.DEFAULT_GOAL := help
SHELL := /bin/bash

API := packages/api
WEB := packages/web
UV  := uv --project $(API)
# Порт для `make dev`. Переопределяется, если 8000 занят: `make dev PORT=8081`.
PORT ?= 8000

.PHONY: help up up-build down logs seed dev schema codegen test test-integration \
        test-db-start test-db-stop lint format typecheck

help: ## Показать список команд
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Запуск ────────────────────────────────────────────────────────────────

up: ## Запустить приложение (образ тянется из ghcr.io) → http://localhost:8000
	docker compose up -d --wait
	@echo ""
	@echo "  ✅ SalesLift готов: http://localhost:8000"
	@echo ""

up-build: ## То же, но собрать образ локально (для разработки, не для клиента)
	docker compose -f compose.yaml -f compose.build.yaml up -d --build --wait
	@echo ""
	@echo "  ✅ SalesLift готов (локальная сборка): http://localhost:8000"
	@echo ""

down: ## Остановить и удалить контейнеры
	docker compose down

logs: ## Логи приложения
	docker compose logs -f app

seed: ## Наполнить БД демо-данными (откажется работать в production)
	$(UV) run python -m saleslift.tools.seed_demo

dev: ## Разработка: БД в Docker, API с hot-reload (порт: make dev PORT=8081)
	docker compose up -d db --wait
	# Через server.py, а не uvicorn CLI: CLI затирает настройку structlog своим log_config.
	cd $(API) && DB_HOST=localhost PORT=$(PORT) uv run python -m saleslift.server

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
