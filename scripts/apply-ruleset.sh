#!/usr/bin/env bash
# Применяет описание защиты ветки из .github/rulesets/main.json к репозиторию.
#
# Настройки репозитория живут не в коде, и это их беда: кто и когда включил
# обязательную проверку — видно только в интерфейсе GitHub, а «почему именно
# эти пять» не видно нигде. Поэтому правила лежат файлом в репозитории, а этот
# скрипт лишь заливает их. Изменение защиты становится обычным коммитом.
#
#   bash scripts/apply-ruleset.sh          # применить
#   bash scripts/apply-ruleset.sh --show   # показать, что сейчас в репозитории
#
# Нужны права администратора репозитория и `gh auth login` со scope `repo`.
# Скрипт идемпотентен: повторный запуск приводит правила к состоянию файла.

set -euo pipefail

RULESET_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.github/rulesets/main.json"

fail() {
  echo "❌ $1" >&2
  exit 1
}

command -v gh > /dev/null || fail "нужен gh: https://cli.github.com"
command -v jq > /dev/null || fail "нужен jq: apt install jq"
[ -f "$RULESET_FILE" ] || fail "не нашёл $RULESET_FILE"

REPO="${REPO:-$(gh repo view --json nameWithOwner --jq .nameWithOwner)}"
NAME="$(jq -r .name "$RULESET_FILE")"

# Набор правил ищем по имени: у API нет способа сказать «создай или обнови»,
# а по имени набор в репозитории уникален.
ID="$(gh api "repos/${REPO}/rulesets" \
  --jq "map(select(.name == \"${NAME}\")) | .[0].id // empty")" \
  || fail "не смог прочитать правила ${REPO} — нужны права администратора"

show() {
  echo "▸ Что сейчас защищает ветку по умолчанию в ${REPO}"
  if [ -z "$ID" ]; then
    echo "  ✖ набора правил «${NAME}» нет — влить красный PR можно без предупреждения"
    return
  fi
  gh api "repos/${REPO}/rulesets/${ID}" --jq '
    "  режим: \(.enforcement)",
    "  правила: \([.rules[].type] | join(", "))",
    "  обязательные проверки:",
    (.rules[] | select(.type == "required_status_checks")
      | .parameters.required_status_checks[] | "    ✔ \(.context)")
  '
}

if [ "${1:-}" = "--show" ]; then
  show
  exit 0
fi

if [ -n "$ID" ]; then
  echo "▸ Обновляю набор правил «${NAME}» (id ${ID})"
  gh api --method PUT "repos/${REPO}/rulesets/${ID}" --input "$RULESET_FILE" > /dev/null \
    || fail "обновить не удалось"
else
  echo "▸ Создаю набор правил «${NAME}»"
  ID="$(gh api --method POST "repos/${REPO}/rulesets" --input "$RULESET_FILE" --jq .id)" \
    || fail "создать не удалось"
fi

echo ""
show
echo ""
echo "  ✅ Готово. Прямой push в ветку по умолчанию больше не пройдёт."
