"""Проверки иерархии доменных ошибок."""

from collections.abc import Callable

import pytest

from saleslift.utils.errors import (
    AppError,
    AuthenticationError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)


def test_все_доменные_ошибки_наследуются_от_AppError() -> None:
    for cls in (NotFoundError, ValidationError, AuthenticationError, ForbiddenError):
        assert issubclass(cls, AppError)


@pytest.mark.parametrize(
    ("factory", "expected_code"),
    [
        (lambda: NotFoundError("users.notFound"), "NOT_FOUND"),
        (lambda: ValidationError("auth.passwordTooShort"), "BAD_USER_INPUT"),
        (lambda: AuthenticationError(), "UNAUTHENTICATED"),
        (lambda: ForbiddenError(), "FORBIDDEN"),
    ],
)
def test_код_ошибки_соответствует_типу(factory: Callable[[], AppError], expected_code: str) -> None:
    assert factory().code == expected_code


def test_ключ_i18n_и_поле_сохраняются() -> None:
    """`field` нужен фронтенду, чтобы подсветить конкретный инпут формы."""
    err = ValidationError("auth.emailTaken", field="email")
    assert err.i18n_key == "auth.emailTaken"
    assert err.field == "email"


def test_у_ошибок_аутентификации_есть_ключ_по_умолчанию() -> None:
    assert AuthenticationError().i18n_key == "auth.unauthenticated"
    assert ForbiddenError().i18n_key == "auth.forbidden"
