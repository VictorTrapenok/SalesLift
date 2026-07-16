"""Русские сообщения об ошибках API.

Набор ключей обязан совпадать с en.py — расхождение ловит tests/unit/test_i18n.py.
"""

MESSAGES: dict[str, str] = {
    # ── Аутентификация ───────────────────────────────────────────────────
    "auth.unauthenticated": "Требуется авторизация",
    "auth.forbidden": "Доступ запрещён",
    "auth.invalidCredentials": "Неверный e-mail или пароль",
    "auth.accountDisabled": "Учётная запись отключена",
    "auth.emailTaken": "Этот e-mail уже зарегистрирован",
    "auth.invalidEmail": "Введите корректный e-mail",
    "auth.passwordTooShort": "Пароль должен быть не короче 8 символов",
    "auth.companyNameRequired": "Введите название компании",
    "auth.nameRequired": "Введите имя",
    "auth.wrongCurrentPassword": "Текущий пароль указан неверно",
    # ── Сотрудники ───────────────────────────────────────────────────────
    "users.notFound": "Сотрудник не найден",
    "users.emailTaken": "Этот e-mail уже зарегистрирован",
    # ── Настройки компании ───────────────────────────────────────────────
    "orgSettings.companyNameRequired": "Введите название компании",
    # ── Профиль ──────────────────────────────────────────────────────────
    "profile.bioTooLong": "Описание не должно быть длиннее 1000 символов",
    "profile.unsupportedLocale": "Язык не поддерживается",
}
