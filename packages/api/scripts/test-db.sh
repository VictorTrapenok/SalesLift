#!/usr/bin/env bash
# Управление тестовым контейнером PostgreSQL.
# Использование: bash scripts/test-db.sh start|stop|wait
#
# Отдельный контейнер на отдельном порту (5433, а не 5432): тестовая база
# полностью изолирована от базы разработки, поэтому прогон тестов никогда не
# затрёт данные, с которыми вы работаете руками. Контейнер одноразовый —
# volume не подключается, стартует всегда с чистого листа.

set -euo pipefail

CONTAINER_NAME="${TEST_DB_CONTAINER:-saleslift-test-db}"
DB_PORT="${TEST_DB_PORT:-5433}"
DB_NAME="${TEST_DB_NAME:-saleslift_test}"
DB_USER="${TEST_DB_USER:-saleslift_test}"
DB_PASSWORD="${TEST_DB_PASSWORD:-test_password}"
PG_IMAGE="${TEST_DB_IMAGE:-postgres:18-alpine}"
WAIT_SECONDS="${TEST_DB_WAIT_SECONDS:-30}"

wait_for_ready() {
  echo -n "Ожидание готовности PostgreSQL"
  for _ in $(seq 1 "$WAIT_SECONDS"); do
    if docker exec "$CONTAINER_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; then
      echo " — готова"
      return 0
    fi
    echo -n "."
    sleep 1
  done
  echo " — таймаут!"
  echo "Логи контейнера:"
  docker logs "$CONTAINER_NAME" 2>&1 | tail -20
  return 1
}

case "${1:-}" in
  start)
    # Убираем контейнер с прошлого прогона, если он остался (например, тесты
    # прервали по Ctrl+C). Тестовая БД всегда стартует с чистого состояния.
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

    echo "Запуск тестовой PostgreSQL на порту $DB_PORT..."
    docker run -d \
      --name "$CONTAINER_NAME" \
      -e POSTGRES_DB="$DB_NAME" \
      -e POSTGRES_USER="$DB_USER" \
      -e POSTGRES_PASSWORD="$DB_PASSWORD" \
      -p "$DB_PORT:5432" \
      "$PG_IMAGE" \
      >/dev/null

    wait_for_ready
    ;;

  stop)
    echo "Остановка тестовой PostgreSQL..."
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
    ;;

  wait)
    wait_for_ready
    ;;

  *)
    echo "Использование: $0 {start|stop|wait}" >&2
    exit 1
    ;;
esac
