"""Английские сообщения об ошибках API.

Эталонная локаль: набор ключей здесь — источник истины, остальные локали
обязаны иметь ровно те же ключи (проверяется tests/unit/test_i18n.py).
"""

MESSAGES: dict[str, str] = {
    # ── Аутентификация ───────────────────────────────────────────────────
    "auth.unauthenticated": "Authentication required",
    "auth.forbidden": "Access denied",
    "auth.invalidCredentials": "Invalid email or password",
    "auth.accountDisabled": "Account is disabled",
    "auth.emailTaken": "This email is already registered",
    "auth.invalidEmail": "Please enter a valid email address",
    "auth.passwordTooShort": "Password must be at least 8 characters",
    "auth.companyNameRequired": "Please enter the company name",
    "auth.nameRequired": "Please enter your name",
    "auth.wrongCurrentPassword": "Current password is incorrect",
    # ── Сотрудники ───────────────────────────────────────────────────────
    "users.notFound": "Employee not found",
    "users.emailTaken": "This email is already registered",
    # ── Настройки компании ───────────────────────────────────────────────
    "orgSettings.companyNameRequired": "Please enter the company name",
    # ── Профиль ──────────────────────────────────────────────────────────
    "profile.bioTooLong": "Bio must be 1000 characters or shorter",
    "profile.unsupportedLocale": "Unsupported language",
}
