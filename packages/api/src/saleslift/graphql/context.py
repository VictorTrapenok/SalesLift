"""Контекст GraphQL-запроса.

Собирает всё, что нужно резолверам: сессию БД, текущего пользователя, его
компанию и локаль.

Профиль и права ЧИТАЮТСЯ ИЗ БД на каждом запросе, а не берутся из токена.
Поэтому изменение прав действует немедленно: разжаловали администратора — он
теряет доступ сразу, а не через неделю, когда протухнет токен. Цена — один
SELECT на запрос.

Сравните с прототипом: там этот файл занимал ~150 строк, потому что тенант
резолвился из поддомена, поддомен сверялся с токеном, для локальной разработки
существовал DEV_TENANT_NAME, для e2e — заголовок-обход, а для админки —
forceAdminTenant. Отказ от поддоменов убрал всё это разом.
"""

from dataclasses import dataclass

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from strawberry.fastapi import BaseContext

from saleslift.i18n import locale_from_accept_language, resolve_locale
from saleslift.models.tenant import Tenant
from saleslift.models.user import User
from saleslift.services.auth.tokens import decode_session_token
from saleslift.utils.errors import AuthenticationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)

_BEARER_PREFIX = "Bearer "


@dataclass
class Context(BaseContext):
    """Контекст одного GraphQL-запроса."""

    session: AsyncSession
    #: Актуальные данные из БД. None — запрос неаутентифицирован.
    current_user: User | None = None
    tenant: Tenant | None = None
    #: Локаль профиля → Accept-Language → 'en'.
    locale: str = "en"


async def build_context(
    session: AsyncSession,
    authorization: str | None,
    accept_language: str | None,
) -> Context:
    """Собирает контекст запроса."""
    user = await _load_user_from_token(session, authorization)

    locale = resolve_locale(user.locale) if user else locale_from_accept_language(accept_language)

    return Context(
        session=session,
        current_user=user,
        tenant=user.tenant if user else None,
        locale=locale,
    )


async def _load_user_from_token(session: AsyncSession, authorization: str | None) -> User | None:
    """Достаёт пользователя по Bearer-токену. None, если токена нет или он плох.

    Невалидный токен — не ошибка запроса: публичные операции (логин,
    регистрация) обязаны работать и с протухшим токеном в заголовке. Отказ
    выдаёт гард `require_auth` в конкретном резолвере, которому авторизация
    действительно нужна.
    """
    if not authorization or not authorization.startswith(_BEARER_PREFIX):
        if authorization:
            log.warning("Заголовок Authorization без схемы Bearer")
        return None

    try:
        payload = decode_session_token(authorization.removeprefix(_BEARER_PREFIX))
    except AuthenticationError:
        # decode_session_token уже залогировал причину.
        return None
    except jwt.PyJWTError as err:
        log.warning("Не удалось разобрать токен", error=str(err))
        return None

    user = await session.scalar(
        # selectinload — компания нужна почти всегда (проверка is_active,
        # вывод в шапке), и без неё каждый доступ к ctx.tenant давал бы
        # отдельный запрос.
        select(User).where(User.id == payload["user_id"]).options(selectinload(User.tenant)),
    )

    if user is None:
        # Токен подписан нами, но пользователя нет: удалён после выдачи токена.
        log.warning("Пользователь из токена не найден", user_id=payload["user_id"])
        return None

    if str(user.tenant_id) != payload["tenant_id"]:
        # Единственная проверка целостности, пережившая отказ от поддоменов.
        # Штатно случиться не может; если случилось — токен подделан или
        # пользователя перенесли между компаниями.
        log.error(
            "tenant_id в токене не совпадает с БД — токен отклонён",
            user_id=str(user.id),
            token_tenant_id=payload["tenant_id"],
            db_tenant_id=str(user.tenant_id),
        )
        return None

    return user
