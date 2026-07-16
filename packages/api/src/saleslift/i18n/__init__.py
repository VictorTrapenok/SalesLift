"""Локализация сообщений API.

Язык запроса определяется в `graphql/context.py`: локаль профиля пользователя →
заголовок `Accept-Language` → `en`.

Ключи плоские, с точкой как частью имени (`auth.invalidCredentials`), и в коде
используются ЦЕЛИКОМ, одной строкой-литералом. Собирать ключ из фрагментов
(`f"auth.{kind}"`) запрещено: такой ключ невозможно найти грепом, и его молча
теряют при рефакторинге.
"""

from typing import Final, Literal, get_args

from saleslift.i18n.en import MESSAGES as EN_MESSAGES
from saleslift.i18n.ru import MESSAGES as RU_MESSAGES

#: Поддерживаемые языки (ISO 639-1). Фронтенд оперирует полными тегами
#: (`ru-RU`), бэкенд — двухбуквенными: маппинг живёт на фронтенде.
Locale = Literal["en", "ru"]
SUPPORTED_LOCALES: Final[tuple[str, ...]] = get_args(Locale)

DEFAULT_LOCALE: Final[str] = "en"

MESSAGES: Final[dict[str, dict[str, str]]] = {
    "en": EN_MESSAGES,
    "ru": RU_MESSAGES,
}


def resolve_locale(value: str | None) -> str:
    """Приводит произвольное значение к поддерживаемой локали.

    Принимает и `ru`, и `ru-RU`: берёт первые две буквы. Неизвестный язык —
    не ошибка, просто откат на `en`.
    """
    if not value:
        return DEFAULT_LOCALE
    code = value.strip().lower()[:2]
    return code if code in SUPPORTED_LOCALES else DEFAULT_LOCALE


def locale_from_accept_language(header: str | None) -> str:
    """Выбирает локаль из заголовка `Accept-Language`.

    Разбор намеренно упрощён: берём первый язык из списка и игнорируем
    q-факторы. Заголовок — лишь запасной вариант (основной источник — локаль
    профиля), поэтому точность приоритетов здесь не окупается.
    """
    if not header:
        return DEFAULT_LOCALE
    first = header.split(",")[0].split(";")[0]
    return resolve_locale(first)


def t(locale: str, key: str) -> str:
    """Возвращает сообщение по ключу.

    Отсутствие перевода не должно ронять запрос: откатываемся на английский,
    затем на сам ключ. Пропущенные ключи ловит tests/unit/test_i18n.py — там
    это ошибка, а в рантайме показать ключ лучше, чем упасть.
    """
    messages = MESSAGES.get(locale) or MESSAGES[DEFAULT_LOCALE]
    if key in messages:
        return messages[key]
    return MESSAGES[DEFAULT_LOCALE].get(key, key)
