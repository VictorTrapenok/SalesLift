#!/usr/bin/env bash
# Дымовой тест собранного образа.
#
# Проверяет не «отвечает ли порт», а работает ли продукт: регистрирует компанию
# и входит под её администратором через настоящий GraphQL. Это тот минимум,
# который обязан работать у клиента после `make up`.
#
# Запускается в CI против собранного образа ДО его публикации: провал означает,
# что образ в registry не попадёт. Локально:
#
#   BASE_URL=http://localhost:8000 bash scripts/smoke-test.sh

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
GQL="${BASE_URL}/api/v1/graphql"

# Уникальные значения: тест может гоняться повторно против той же базы, а e-mail
# глобально уникален.
SUFFIX="$(date +%s)-$$"
EMAIL="smoke-${SUFFIX}@example.com"
PASSWORD="smokeTestPass123"
COMPANY="Smoke Test ${SUFFIX}"

fail() {
  echo "❌ $1" >&2
  exit 1
}

gql() {
  curl -sS --fail-with-body -X POST "$GQL" \
    -H 'Content-Type: application/json' \
    -H 'Accept-Language: ru-RU' \
    --data "$1"
}

echo "▸ Проверяю пробу живости"
HEALTH="$(curl -sS --fail-with-body "${BASE_URL}/api/v1/health")" \
  || fail "health не ответил"
echo "$HEALTH" | grep -q '"status":"ok"' || fail "health вернул не ok: $HEALTH"
echo "  ✔ $HEALTH"

echo "▸ Регистрирую компанию"
REGISTER="$(gql "$(cat <<JSON
{"query":"mutation Register(\$input: RegisterInput!) { resolverAuthRegister(input: \$input) { token user { id email effectivePermissions tenant { id name } } } }",
 "variables":{"input":{"companyName":"${COMPANY}","adminName":"Смоук Тест","email":"${EMAIL}","password":"${PASSWORD}","locale":"ru"}}}
JSON
)")" || fail "мутация регистрации не выполнилась"

echo "$REGISTER" | grep -q '"errors"' && fail "регистрация вернула ошибку: $REGISTER"
echo "$REGISTER" | grep -q '"token"' || fail "регистрация не вернула токен: $REGISTER"
# Первый зарегистрировавшийся обязан стать администратором — иначе он не сможет
# завести остальных, и продукт бесполезен.
echo "$REGISTER" | grep -q '"Admin"' || fail "администратор не получил прав: $REGISTER"
echo "  ✔ компания создана, администратор получил права"

echo "▸ Вхожу под созданным администратором"
LOGIN="$(gql "$(cat <<JSON
{"query":"mutation Login(\$input: LoginInput!) { resolverAuthLogin(input: \$input) { token user { email } } }",
 "variables":{"input":{"email":"${EMAIL}","password":"${PASSWORD}"}}}
JSON
)")" || fail "мутация входа не выполнилась"

echo "$LOGIN" | grep -q '"errors"' && fail "вход вернул ошибку: $LOGIN"
# Пробел после двоеточия обязателен в шаблоне: сервер отдаёт `"token": "..."`,
# и регулярка без ` *` молча не находила токен, хотя тот был на месте.
TOKEN="$(echo "$LOGIN" | sed -n 's/.*"token": *"\([^"]*\)".*/\1/p')"
[ -n "$TOKEN" ] || fail "вход не вернул токен: $LOGIN"
echo "  ✔ вход выполнен"

echo "▸ Читаю профиль по токену"
ME="$(curl -sS --fail-with-body -X POST "$GQL" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${TOKEN}" \
  --data '{"query":"{ resolverAuthMe { email tenant { name } } }"}')" \
  || fail "запрос профиля не выполнился"

echo "$ME" | grep -q "$EMAIL" || fail "профиль вернул не того пользователя: $ME"
echo "  ✔ профиль получен"

echo "▸ Проверяю, что неавторизованный запрос отклоняется"
UNAUTH="$(curl -sS -X POST "$GQL" -H 'Content-Type: application/json' \
  --data '{"query":"{ resolverAuthMe { email } }"}')"
echo "$UNAUTH" | grep -q 'UNAUTHENTICATED' \
  || fail "запрос без токена НЕ был отклонён — дыра в авторизации: $UNAUTH"
echo "  ✔ отклонён с UNAUTHENTICATED"

echo "▸ Проверяю раздачу интерфейса"
INDEX="$(curl -sS --fail-with-body "${BASE_URL}/login")" || fail "SPA не отдалась"
echo "$INDEX" | grep -qi '<div id="root">' || fail "по /login пришёл не SPA: $INDEX"
echo "  ✔ SPA отдаётся, клиентский роутинг работает"

echo ""
echo "✅ Дымовой тест пройден: образ работоспособен"
