"""Преобразование доменных ошибок в GraphQL-ошибки.

Граница между сервисным слоем и транспортом. Сервисы и гарды бросают
`AppError` с ключом i18n; здесь ключ превращается в локализованное сообщение,
а тип ошибки — в `extensions.code`, по которому фронтенд принимает решения
(например, `UNAUTHENTICATED` → разлогинить).

Почему расширение схемы, а не обёртка в резолвере
-------------------------------------------------
В прототипе каждый резолвер оборачивал вызов сервиса руками::

    try { ... } catch (err) { throw mapToGraphQLError(err, locale); }

Такой механизм можно забыть — и это не теория: первая же реализация с ручной
обёрткой отдавала клиенту сырой ключ `auth.unauthenticated` без `code`, потому
что гард `require_auth` бросает ошибку ДО вызова сервиса и в обёртку не попадал.

Расширение перехватывает `AppError` из любого места — резолвера, гарда,
сервиса, — и забыть его невозможно: оно подключено к схеме один раз.
"""

import inspect
from typing import Any

from graphql import GraphQLError
from strawberry.extensions import SchemaExtension

from saleslift.i18n import t
from saleslift.utils.errors import AppError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)

#: Ожидаемые коды: это нормальный ход событий (неверный пароль, занятый
#: e-mail), а не поломка. Логируем их на уровне warning, чтобы они не мусорили
#: в error-логах и не забивали реальные аварии.
_EXPECTED_CODES = frozenset({"NOT_FOUND", "BAD_USER_INPUT", "UNAUTHENTICATED", "FORBIDDEN"})

_DEFAULT_LOCALE = "en"


def map_to_graphql_error(err: AppError, locale: str) -> GraphQLError:
    """Превращает доменную ошибку в GraphQL-ошибку с локализованным сообщением."""
    message = t(locale, err.i18n_key) if err.i18n_key else str(err)

    extensions: dict[str, object] = {"code": err.code}
    if err.field:
        # Поле, на котором споткнулась валидация: фронтенд подсветит им инпут.
        extensions["field"] = err.field

    return GraphQLError(message, extensions=extensions)


class DomainErrorExtension(SchemaExtension):
    """Перехватывает доменные ошибки и локализует их.

    Ловим только `AppError`. Всё остальное — баг, и его должен увидеть
    обработчик схемы: подменять неожиданное исключение вежливым сообщением
    значит прятать аварию от мониторинга.
    """

    async def resolve(
        self,
        _next: Any,
        root: Any,
        info: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Оборачивает разрешение каждого поля схемы."""
        try:
            result = _next(root, info, *args, **kwargs)
            # Резолверы бывают и синхронные, и асинхронные.
            if inspect.isawaitable(result):
                result = await result
            return result
        except AppError as err:
            locale = getattr(info.context, "locale", _DEFAULT_LOCALE)

            if err.code in _EXPECTED_CODES:
                log.warning("Доменная ошибка", code=err.code, i18n_key=err.i18n_key, field=err.field)
            else:
                log.error("Неожиданная доменная ошибка", code=err.code, i18n_key=err.i18n_key)

            raise map_to_graphql_error(err, locale) from err
