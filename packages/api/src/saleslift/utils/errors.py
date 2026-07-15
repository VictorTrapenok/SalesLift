"""Доменные ошибки приложения.

Сервисы бросают эти ошибки — резолверы преобразуют их в GraphQL-ошибки через
`map_to_graphql_error()` из `graphql/errors.py`. Сервисный слой ничего не знает
ни про GraphQL, ни про HTTP: он говорит на языке предметной области.

Сообщение для пользователя не хранится в ошибке — хранится ключ i18n. Локаль
известна только на границе запроса, поэтому текст подставляется там же, в
резолвере, а не в месте выброса.
"""


class AppError(Exception):
    """Базовый класс доменной ошибки."""

    def __init__(
        self,
        message: str,
        code: str,
        i18n_key: str | None = None,
        field: str | None = None,
    ) -> None:
        """
        :param message: техническое сообщение для логов
        :param code: код ошибки, уезжает в GraphQL extensions.code
        :param i18n_key: ключ перевода для сообщения пользователю;
                         если не задан — используется message
        :param field: имя поля, вызвавшего ошибку — фронтенд подсвечивает им форму
        """
        super().__init__(message)
        self.code = code
        self.i18n_key = i18n_key
        self.field = field


class NotFoundError(AppError):
    """Запрошенный ресурс не найден."""

    def __init__(self, i18n_key: str, field: str | None = None) -> None:
        super().__init__(i18n_key, "NOT_FOUND", i18n_key, field)


class ValidationError(AppError):
    """Входные данные не прошли проверку."""

    def __init__(self, i18n_key: str, field: str | None = None) -> None:
        super().__init__(i18n_key, "BAD_USER_INPUT", i18n_key, field)


class AuthenticationError(AppError):
    """Не аутентифицирован: токена нет, он невалиден или учётные данные неверны."""

    def __init__(self, i18n_key: str = "auth.unauthenticated") -> None:
        super().__init__(i18n_key, "UNAUTHENTICATED", i18n_key)


class ForbiddenError(AppError):
    """Аутентифицирован, но прав на операцию нет."""

    def __init__(self, i18n_key: str = "auth.forbidden") -> None:
        super().__init__(i18n_key, "FORBIDDEN", i18n_key)
