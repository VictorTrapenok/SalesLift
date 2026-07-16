# Разработка

Как поднять рабочее окружение и что нужно знать, прежде чем править код.

Просто запустить продукт и посмотреть — [README](../README.md), там одна
команда. Этот документ для тех, кто собирается менять код.

## Требования

| Инструмент | Версия | Зачем                                        |
| ---------- | ------ | -------------------------------------------- |
| Docker     | любая  | PostgreSQL, тестовая база, сборка образа      |
| uv         | 0.11+  | Пакетный менеджер Python. **Сам поставит Python 3.13** |
| Node.js    | 24+    | Фронтенд                                      |

Python ставить руками не нужно: `uv` принесёт нужную версию.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Первый запуск

```bash
make db-migrate   # поднимет PostgreSQL в Docker и накатит схему
make dev-api      # первый терминал:  API на :8000, hot-reload
make dev-web      # второй терминал:  интерфейс на :5173, hot-reload
```

Открыть http://localhost:5173.

Работать нужно именно через **5173**: Vite отдаёт фронтенд с горячей
перезагрузкой и проксирует `/api` на бэкенд, поэтому всё идёт с одного origin —
ровно как в production, где бэкенд раздаёт собранную SPA сам.

**Порт 8000 занят?**

```bash
make dev-api PORT=8081
make dev-web PORT=8081   # скажет Vite, куда проксировать /api
```

Никаких `.env` создавать не нужно: рабочие значения по умолчанию лежат в
[.env.example](../.env.example) и коммитятся. Личные переопределения — в `.env`
(он в `.gitignore`).

## Что где слушает

| Адрес                                | Что                                       |
| ------------------------------------ | ----------------------------------------- |
| http://localhost:5173                | Интерфейс (Vite, hot-reload)              |
| http://localhost:8000/api/v1/graphql | GraphQL API + GraphiQL в браузере         |
| http://localhost:8000/api/v1/health  | Проба живости                             |
| `localhost:5432`                     | PostgreSQL разработки                     |
| `localhost:5433`                     | PostgreSQL тестов (только на время прогона) |

## Команды

`make` без аргументов покажет весь список.

```bash
make dev-api          # БД + API с hot-reload
make dev-web          # фронтенд с hot-reload
make db-migrate       # накатить миграции

make test             # unit-тесты (доли секунды, без БД)
make test-integration # интеграционные (поднимут PostgreSQL в Docker)

make codegen          # схема бэкенда → типы фронтенда
make lint             # ruff + eslint
make format           # ruff format + prettier
make typecheck        # mypy --strict + tsc --noEmit

make up               # собрать образ и запустить как у клиента
make logs             # логи контейнера
make reset            # остановить и УДАЛИТЬ данные
```

## ⚠️ После изменения GraphQL-схемы — `make codegen`

Это не формальность, а несущая конструкция проекта.

Типы фронтенда генерируются из схемы бэкенда, и каждый запрос `gql` в
компонентах валидируется против неё. Переименовали поле на бэкенде и забыли
фронтенд — codegen падает с указанием файла и строки:

```
Cannot query field "bio" on type "User". Did you mean "id"?
  at src/hooks/useCurrentUser.ts:7:7
```

Тот же механизм работает в Docker-сборке: стейдж `web-builder` запускает
codegen до `vite build`, поэтому рассинхронизованный образ физически не
соберётся и не уедет в registry.

`packages/api/schema.graphql` **коммитится**: это контракт API, его изменения
видны в diff'е при ревью. `packages/web/src/graphql/generated/` — наоборот, в
`.gitignore`: артефакт сборки.

Подробности — [packages/web/src/graphql/readme.md](../packages/web/src/graphql/readme.md).

## Миграции

```bash
cd packages/api
DB_HOST=localhost uv run alembic revision --autogenerate -m "описание" --rev-id 0002
DB_HOST=localhost uv run alembic upgrade head
DB_HOST=localhost uv run alembic check    # расходятся ли модели со схемой
```

Autogenerate даёт **черновик**: читайте глазами и прогоняйте
`upgrade → downgrade → upgrade`. Правила и подводные камни —
[migrations/readme.md](../packages/api/src/saleslift/migrations/readme.md).

## Тесты

Устройство, правила и как писать новые — [docs/testing.md](testing.md).

Коротко: `make test` — без БД, `make test-integration` — на реальной
PostgreSQL. **Запускать только через `make`** либо с `--env-file .env.test`:
тесты делают `TRUNCATE`, и без этого флага настройки укажут на базу разработки.

## Структура

```
packages/api/src/saleslift/
  config/       настройки, константы, информация о сборке
  db/           движок, сессии, миксины, мягкое удаление   → readme.md
  models/       ORM-модели, явный реестр                    → readme.md
  migrations/   Alembic                                     → readme.md
  graphql/      схема, контекст, типы, резолверы, ошибки
  services/     бизнес-логика
  i18n/         локализация сообщений API
  utils/        доменные ошибки, логгер

packages/web/src/
  graphql/      Apollo-клиент, сгенерированные типы         → readme.md
  i18n/         локали ru/en                                → readme.md
  pages/        страницы: index.tsx + queries.ts + components/
  components/   переиспользуемое между страницами
  hooks/        useCurrentUser — профиль и права
```

Детали живут в `readme.md` рядом с кодом. Общая картина —
[ARCHITECTURE.md](../ARCHITECTURE.md), правила и стиль — [CLAUDE.md](../CLAUDE.md).

## Отладка

**База разработки:**

```bash
docker compose exec db psql -U saleslift -d saleslift -c "\d users"
```

**GraphiQL** — http://localhost:8000/api/v1/graphql в браузере. Доступен вне
production.

**Логи** в разработке человекочитаемые, в production и тестах — JSON.
Подробности: `LOG_LEVEL=debug`.

## Частые грабли

**В интерфейсе видны ключи вместо текста** (`auth.login.title`). Сломали
`keySeparator: false` / `nsSeparator: false` в `src/i18n/index.ts`. Подробности
— [i18n/readme.md](../packages/web/src/i18n/readme.md).

**`MissingGreenlet` или «ленивая загрузка вне await».** Забыли `selectinload`
для связи. Модели объявлены с `lazy="raise"` намеренно: это ловит N+1 явной
ошибкой вместо тихой деградации.

**Тесты падают с `deadlock detected` или гонками миграций.** Кто-то добавил
`pytest-xdist`. Не надо — [почему](testing.md).

**Сборка образа падает со `snapshot ... does not exist: not found`.** Дефект
buildkit в отдельных версиях Docker: проявляется на многостадийных сборках,
переживает `docker builder prune -af` и не связан с местом на диске.

Обход — собирать изолированным сборщиком:

```bash
docker buildx create --name saleslift-builder --driver docker-container --use
docker buildx build -f Dockerfile -t saleslift:local --load .
```

Сборщик живёт в контейнере со своим снапшоттером и дефекту демона не подвержен.
