"""Разбор длительностей вида `7d`, `24h`, `30m`.

Формат унаследован от конфигурации прототипа (`JWT_EXPIRES_IN=7d`) — он
привычен и читаем в .env. У PyJWT аналога `expiresIn` из jsonwebtoken нет,
поэтому парсер свой.
"""

import re
from datetime import timedelta

_DURATION_RE = re.compile(r"^(\d+)([smhd])$")

_UNIT_TO_KWARG = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
}


def parse_duration(value: str) -> timedelta:
    """Разбирает строку длительности в timedelta.

    Поддерживаемые единицы: `s` (секунды), `m` (минуты), `h` (часы), `d` (дни).

    :raises ValueError: формат не распознан. Это ошибка конфигурации, и
        поднимать её нужно на старте, а не молча подставлять умолчание:
        неверный `JWT_EXPIRES_IN` иначе обернулся бы токенами с неожиданным
        сроком жизни.
    """
    match = _DURATION_RE.match(value.strip())
    if match is None:
        raise ValueError(f"Некорректная длительность: {value!r}. Ожидается формат вида '7d', '24h', '30m', '60s'.")

    amount, unit = match.groups()
    return timedelta(**{_UNIT_TO_KWARG[unit]: int(amount)})
