"""Регистрация компаний и вход сотрудников.

Вся бизнес-логика auth здесь; резолверы — тонкая обёртка. Подробности сценариев
и контракт нормализации e-mail — в readme.md и registration-and-login.md рядом.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime

import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saleslift.i18n import resolve_locale
from saleslift.models.tenant import Tenant
from saleslift.models.user import User
from saleslift.services.auth.tokens import sign_session_token
from saleslift.utils.errors import AuthenticationError, ValidationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)

#: Санити-проверка формата. Полная валидация e-mail возможна только отправкой
#: письма, поэтому городить сложную регулярку смысла нет.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

MIN_PASSWORD_LENGTH = 8

#: Стоимость bcrypt. 12 — как в прототипе: заметно дороже дефолтных 10 для
#: перебора, но всё ещё ~100 мс на логин.
_BCRYPT_ROUNDS = 12

#: Хеш-пустышка для сравнения, когда пользователь не найден. Нужен, чтобы
#: ответ «неверный e-mail» занимал столько же времени, сколько «неверный
#: пароль»: иначе по задержке перебирается, какие адреса зарегистрированы.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-for-constant-time-compare", bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))


@dataclass(frozen=True)
class RegisterInput:
    """Данные формы регистрации компании."""

    company_name: str
    admin_name: str
    email: str
    password: str
    #: Язык интерфейса на момент регистрации — сохраняется в профиль админа.
    locale: str = "en"


@dataclass(frozen=True)
class LoginInput:
    """Данные формы входа. Компании здесь нет: она выводится из e-mail."""

    email: str
    password: str


@dataclass(frozen=True)
class AuthPayload:
    """Результат успешной регистрации или входа."""

    token: str
    user: User


def hash_password(password: str) -> str:
    """Хеширует пароль bcrypt'ом."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет пароль против хеша."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def normalize_email(email: str) -> str:
    """Приводит e-mail к каноническому виду.

    Вызывать ПЕРЕД каждой записью и каждым поиском. Уникальный индекс построен
    по обычной колонке, а не по `lower(email)`, поэтому дисциплина обязательна:
    без неё «Ivan@Mail.ru» и «ivan@mail.ru» станут разными пользователями.
    """
    return email.strip().lower()


class AuthService:
    """Регистрация компаний и вход сотрудников."""

    async def register(
        self,
        session: AsyncSession,
        data: RegisterInput,
        locale: str,
    ) -> AuthPayload:
        """Создаёт компанию и её первого администратора.

        Первый зарегистрировавшийся становится администратором: у компании
        должен быть кто-то, кто заведёт остальных.

        Тенант и пользователь создаются в ОДНОЙ транзакции: компания без
        единого сотрудника недоступна никому и мусорит в базе.
        """
        company_name = data.company_name.strip()
        admin_name = data.admin_name.strip()
        email = normalize_email(data.email)

        if not company_name:
            raise ValidationError("auth.companyNameRequired", field="companyName")
        if not admin_name:
            raise ValidationError("auth.nameRequired", field="adminName")
        if not _EMAIL_RE.match(email):
            raise ValidationError("auth.invalidEmail", field="email")
        if len(data.password) < MIN_PASSWORD_LENGTH:
            raise ValidationError("auth.passwordTooShort", field="password")

        # Проверка занятости — любезность ради внятной ошибки в форме.
        # Настоящая гарантия — частичный уникальный индекс uq_users_email,
        # см. обработку IntegrityError ниже.
        existing = await session.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            raise ValidationError("auth.emailTaken", field="email")

        tenant = Tenant(name=company_name)
        user = User(
            tenant=tenant,
            name=admin_name,
            email=email,
            password_hash=hash_password(data.password),
            permissions=["admin"],
            status="active",
            locale=resolve_locale(data.locale),
        )
        session.add(user)

        try:
            await session.commit()
        except IntegrityError as err:
            await session.rollback()
            # Между проверкой выше и вставкой кто-то занял тот же адрес.
            # Окно крошечное, но при регистрации по ссылке из рассылки два
            # клика подряд попадают в него регулярно.
            log.warning("Гонка при регистрации: e-mail уже занят", email=email)
            raise ValidationError("auth.emailTaken", field="email") from err

        log.info("Зарегистрирована компания", tenant_id=str(tenant.id), user_id=str(user.id))
        return AuthPayload(token=_issue_token(user), user=user)

    async def login(
        self,
        session: AsyncSession,
        data: LoginInput,
        locale: str,
    ) -> AuthPayload:
        """Проверяет учётные данные и выдаёт сессионный токен.

        Поиск пользователя по e-mail — И ЕСТЬ резолвинг тенанта: компания
        читается со строки найденного пользователя. Ни поддомена, ни поля
        «компания» в форме.
        """
        email = normalize_email(data.email)

        user = await session.scalar(
            select(User).where(User.email == email).options(selectinload(User.tenant)),
        )

        if user is None or user.password_hash is None:
            # Сравниваем с хешем-пустышкой, чтобы потратить столько же
            # времени, сколько на реальную проверку: разница в задержке
            # выдала бы, зарегистрирован ли адрес.
            bcrypt.checkpw(data.password.encode(), _DUMMY_HASH)
            raise AuthenticationError("auth.invalidCredentials")

        if not verify_password(data.password, user.password_hash):
            raise AuthenticationError("auth.invalidCredentials")

        # Причину блокировки не уточняем: сообщение одно и то же и для
        # отключённого сотрудника, и для отключённой компании.
        if user.status != "active" or not user.tenant.is_active:
            log.info("Вход отклонён: учётная запись неактивна", user_id=str(user.id), status=user.status)
            raise AuthenticationError("auth.accountDisabled")

        user.last_login_at = _utc_now()
        await session.commit()

        return AuthPayload(token=_issue_token(user), user=user)


def _issue_token(user: User) -> str:
    """Выпускает сессионный токен для пользователя."""
    return sign_session_token(user_id=user.id, tenant_id=user.tenant_id)


def _utc_now() -> datetime:
    """Текущее время в UTC."""
    return datetime.now(UTC)


#: Синглтон сервиса — как в прототипе, без DI-контейнера.
auth_service = AuthService()
