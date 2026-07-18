"""Сотрудники компании: список и заведение новых.

Здесь всё, что администратор делает с ЧУЖИМИ учётными записями.
Самообслуживание — своё «о себе» и свой пароль — в `profile_service.py` рядом.

Приглашений по ссылке нет: администратор задаёт сотруднику пароль сам и
передаёт его любым удобным способом. Флоу приглашений появится вместе с
почтовой рассылкой, и тогда же в `models/user.py` вернутся статусы `invited`
и `pending`.

Каждый запрос скоупится компанией явным `.where(User.tenant_id == tenant_id)`.
Магии в ORM нет: мультитенантность здесь держится на дисциплине и на тестах
«не видит чужой тенант».
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saleslift.i18n import resolve_locale
from saleslift.models.user import USER_ROLE_NAMES, User
from saleslift.services.auth.auth_service import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    is_valid_email,
    normalize_email,
)
from saleslift.utils.errors import ValidationError
from saleslift.utils.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class CreateEmployeeInput:
    """Данные формы «новый сотрудник»."""

    name: str
    email: str
    password: str
    #: Маркер базовой роли: `admin` / `manager` / `viewer`.
    role: str
    #: Язык серверных сообщений для заводимого сотрудника.
    locale: str = "en"


class UsersService:
    """Список сотрудников компании и заведение новых."""

    async def list_employees(self, session: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
        """Возвращает всех живых сотрудников компании, отсортированных по имени.

        `selectinload(User.tenant)` обязателен: GraphQL-тип `User` собирает
        вложенную компанию, а связи объявлены с `lazy="raise"` — без него
        сборка ответа упала бы явной ошибкой. Одним запросом на всю выборку,
        а не по сотруднику: это и есть защита от N+1.

        Пагинации нет намеренно: у компании до MVP десятки сотрудников, а не
        тысячи. Появится вместе с первым клиентом, которому она понадобится.
        """
        result = await session.scalars(
            select(User).where(User.tenant_id == tenant_id).options(selectinload(User.tenant)).order_by(User.name),
        )
        return list(result)

    async def create_employee(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        data: CreateEmployeeInput,
    ) -> User:
        """Заводит сотрудника в компании и сразу задаёт ему пароль."""
        name = data.name.strip()
        email = normalize_email(data.email)

        if not name:
            raise ValidationError("auth.nameRequired", field="name")
        if not is_valid_email(email):
            raise ValidationError("auth.invalidEmail", field="email")
        if len(data.password) < MIN_PASSWORD_LENGTH:
            raise ValidationError("auth.passwordTooShort", field="password")
        if data.role not in USER_ROLE_NAMES:
            raise ValidationError("users.invalidRole", field="role")

        # Проверка занятости — любезность ради внятной ошибки в форме.
        # Настоящая гарантия — частичный уникальный индекс uq_users_email,
        # см. обработку IntegrityError ниже. E-mail уникален ГЛОБАЛЬНО, а не
        # внутри компании, поэтому здесь нет фильтра по tenant_id: адрес,
        # занятый в чужой компании, занят и здесь.
        existing = await session.scalar(select(User.id).where(User.email == email))
        if existing is not None:
            raise ValidationError("users.emailTaken", field="email")

        user = User(
            tenant_id=tenant_id,
            name=name,
            email=email,
            password_hash=hash_password(data.password),
            permissions=[data.role],
            status="active",
            locale=resolve_locale(data.locale),
        )
        session.add(user)

        try:
            await session.commit()
        except IntegrityError as err:
            await session.rollback()
            # Между проверкой выше и вставкой адрес заняли: два клика по
            # кнопке «Добавить» попадают в это окно регулярно.
            log.warning("Гонка при заведении сотрудника: e-mail уже занят", email=email)
            raise ValidationError("users.emailTaken", field="email") from err

        # Компания нужна GraphQL-типу `User`, а после commit она не загружена.
        await session.refresh(user, ["tenant"])

        log.info("Заведён сотрудник", tenant_id=str(tenant_id), user_id=str(user.id), role=data.role)
        return user


#: Синглтон сервиса — как и остальные сервисы, без DI-контейнера.
users_service = UsersService()
