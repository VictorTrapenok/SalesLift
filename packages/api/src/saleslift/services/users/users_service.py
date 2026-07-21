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
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from saleslift.i18n import resolve_locale
from saleslift.models.user import USER_ROLE_NAMES, USER_STATUSES, User
from saleslift.services.auth.auth_service import (
    MIN_PASSWORD_LENGTH,
    hash_password,
    is_valid_email,
    normalize_email,
)
from saleslift.services.users.user_roles_permission import USERS_ROLE_MAP
from saleslift.utils.errors import NotFoundError, ValidationError
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

    async def change_role(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
    ) -> User:
        """Меняет базовую роль сотрудника.

        Точечные добавки к правам (значения `UserPermissions` сверх роли)
        сохраняются: меняется только маркер роли, а не весь набор.
        """
        if role not in USER_ROLE_NAMES:
            raise ValidationError("users.invalidRole", field="role")

        employee = await self._get_own_employee(session, tenant_id, actor_id, user_id)

        # Маркер роли заменяется, гранулярные добавки остаются на месте.
        # `list(...)` — новый объект, иначе SQLAlchemy не заметит изменение
        # JSONB-колонки и UPDATE не уйдёт.
        extras = [entry for entry in employee.permissions if entry not in USERS_ROLE_MAP]
        employee.permissions = [role, *extras]

        await session.commit()

        log.info("Сменена роль сотрудника", tenant_id=str(tenant_id), user_id=str(user_id), role=role)
        return employee

    async def set_status(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str,
    ) -> User:
        """Отключает (`suspended`) или включает (`active`) учётную запись.

        Отключённому сотруднику вход запрещён немедленно: контекст перечитывает
        статус из БД на каждом запросе (см. `auth_service.login` и
        `graphql/context.py`).
        """
        if status not in USER_STATUSES:
            raise ValidationError("users.invalidStatus", field="status")

        employee = await self._get_own_employee(session, tenant_id, actor_id, user_id)
        employee.status = status

        await session.commit()

        log.info("Изменён статус сотрудника", tenant_id=str(tenant_id), user_id=str(user_id), status=status)
        return employee

    async def delete_employee(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User:
        """Мягко удаляет сотрудника: строка остаётся, но пропадает из выборок.

        Возвращает уже удалённую модель — резолвер собирает из неё ответ.
        Повторно из БД её не вычитать: глобальный фильтр мягкого удаления
        спрячет строку. Поэтому связь `tenant` загружена заранее, в
        `_get_own_employee`, а `expire_on_commit=False` не даёт коммиту
        сбросить загруженные поля.

        E-mail при этом освобождается: уникальный индекс `uq_users_email`
        частичный (только живые строки), поэтому адрес уволенного можно завести
        заново.
        """
        employee = await self._get_own_employee(session, tenant_id, actor_id, user_id)
        employee.deleted_at = datetime.now(UTC)

        await session.commit()

        log.info("Удалён сотрудник", tenant_id=str(tenant_id), user_id=str(user_id))
        return employee

    async def _get_own_employee(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> User:
        """Находит сотрудника компании для управляющего действия.

        Три проверки в одном месте, потому что нужны они всем трём операциям —
        смене роли, статуса и удалению:

        1. `tenant_id` в запросе — сотрудника чужой компании не тронуть даже
           зная его id.
        2. Действие над собой запрещено. Отключить или удалить себя — мгновенно
           лишиться доступа; сменить себе роль — потерять права, которыми это
           действие и разрешено. А поскольку право управления сотрудниками есть
           только у администратора, запрет на действие над собой заодно
           гарантирует, что последнего администратора компании не разжаловать и
           не удалить: сделать это мог бы лишь другой администратор, который
           после операции останется.
        3. Сотрудник существует.

        Связь `tenant` грузится сразу: она нужна GraphQL-типу `User`, а после
        commit'а (особенно удаляющего) отдельной подгрузкой её уже не достать.
        """
        if user_id == actor_id:
            raise ValidationError("users.cannotManageSelf")

        employee = await session.scalar(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id).options(selectinload(User.tenant)),
        )
        if employee is None:
            raise NotFoundError("users.notFound")

        return employee


#: Синглтон сервиса — как и остальные сервисы, без DI-контейнера.
users_service = UsersService()
