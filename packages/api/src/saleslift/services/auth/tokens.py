"""Выпуск и проверка JWT.

В payload только идентификаторы. Профиль, права и локаль перечитываются из БД
на КАЖДОМ запросе (см. `graphql/context.py`), поэтому изменения вступают в силу
немедленно, без перевыпуска токена: разжаловали администратора — он теряет
права сразу, а не через неделю, когда протухнет токен.

`tenant_slug` из прототипа здесь нет: там он был нужен только для сверки с
поддоменом, а поддоменов не существует.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal, TypedDict

import jwt

from saleslift.config.settings import settings
from saleslift.utils.duration import parse_duration
from saleslift.utils.errors import AuthenticationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)

_ALGORITHM = "HS256"

#: Тип токена. Сейчас реализован только `session`; `reset` и `invite`
#: перечислены, чтобы форма payload'а была задана заранее — но кода под них
#: нет и не будет, пока не появятся сами сценарии.
TokenType = Literal["session", "reset", "invite"]


class SessionTokenPayload(TypedDict):
    """Полезная нагрузка сессионного токена."""

    type: TokenType
    user_id: str
    tenant_id: str
    iat: int
    exp: int


def sign_session_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """Выпускает сессионный токен на срок `JWT_EXPIRES_IN`."""
    now = datetime.now(UTC)
    expires_at = now + parse_duration(settings.jwt_expires_in)

    payload: SessionTokenPayload = {
        "type": "session",
        "user_id": str(user_id),
        "tenant_id": str(tenant_id),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    # dict(...) — TypedDict не подходит под сигнатуру jwt.encode (она ждёт
    # dict[str, Any]), хотя в рантайме это тот же словарь.
    return jwt.encode(dict(payload), settings.jwt_secret, algorithm=_ALGORITHM)


def decode_session_token(token: str) -> SessionTokenPayload:
    """Проверяет подпись и срок действия сессионного токена.

    :raises AuthenticationError: токен невалиден, просрочен или не того типа.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.InvalidTokenError as err:
        # Логируем, но наружу отдаём обезличенную ошибку: детали разбора
        # токена — подсказка атакующему.
        log.warning("Не удалось разобрать JWT", error=str(err))
        raise AuthenticationError() from err

    if payload.get("type") != "session":
        # Токен сброса пароля или приглашения не должен открывать сессию:
        # у них другой сценарий и другой срок жизни.
        log.warning("Токен неверного типа предъявлен как сессионный", token_type=payload.get("type"))
        raise AuthenticationError()

    return SessionTokenPayload(
        type="session",
        user_id=payload["user_id"],
        tenant_id=payload["tenant_id"],
        iat=payload["iat"],
        exp=payload["exp"],
    )
