"""Проверки тестовой обвязки и механизмов слоя БД.

Тесты намеренно написаны до появления бизнес-логики: они доказывают, что
обвязка работает, а невидимые механизмы (мягкое удаление, частичный уникальный
индекс) ведут себя так, как обещано в документации.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from saleslift.db.soft_delete import include_deleted
from saleslift.models import Tenant, User


async def test_фикстура_создаёт_компанию_с_дефолтами(tenant: Tenant) -> None:
    """Серверные дефолты проставляются базой, а не Python-кодом."""
    assert tenant.id is not None
    assert tenant.plan == "free"
    assert tenant.is_active is True
    assert tenant.deleted_at is None
    assert tenant.created_at is not None


async def test_фикстура_создаёт_админа_привязанного_к_компании(admin_user: User, tenant: Tenant) -> None:
    assert admin_user.tenant_id == tenant.id
    assert admin_user.permissions == ["admin"]
    assert admin_user.status == "active"


async def test_email_нормализуется_при_записи(session: AsyncSession, tenant: Tenant) -> None:
    """Валидатор модели — вторая линия защиты уникального индекса.

    Индекс построен по обычной колонке, а не по lower(email), поэтому
    «Ivan@Example.COM» без нормализации считался бы другим адресом.
    """
    user = User(
        tenant_id=tenant.id,
        name="Иван",
        email="  Ivan@Example.COM  ",
        permissions=["admin"],
    )
    session.add(user)
    await session.commit()

    assert user.email == "ivan@example.com"


async def test_email_уникален_глобально_а_не_внутри_компании(
    session: AsyncSession,
    tenant: Tenant,
    other_tenant: Tenant,
) -> None:
    """Ключевое отличие от прототипа.

    Там e-mail был уникален в пределах тенанта, потому что компания
    определялась поддоменом. Здесь поддоменов нет и компания выводится из
    строки пользователя — значит, адрес обязан быть уникален глобально.
    """
    email = f"duplicate-{uuid.uuid4().hex[:8]}@example.com"
    session.add(User(tenant_id=tenant.id, name="Первый", email=email, permissions=["admin"]))
    await session.commit()

    session.add(User(tenant_id=other_tenant.id, name="Второй", email=email, permissions=["admin"]))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_мягко_удалённый_пользователь_исчезает_из_выборок(
    session: AsyncSession,
    admin_user: User,
) -> None:
    """Аналог `paranoid: true`: фильтр навешивается на каждый SELECT."""
    admin_user.deleted_at = datetime.now(UTC)
    await session.commit()

    found = await session.scalar(select(User).where(User.id == admin_user.id))
    assert found is None


async def test_include_deleted_возвращает_удалённых(session: AsyncSession, admin_user: User) -> None:
    """Лазейка для админских сценариев и восстановления."""
    admin_user.deleted_at = datetime.now(UTC)
    await session.commit()

    stmt = select(User).where(User.id == admin_user.id).execution_options(**include_deleted())
    found = await session.scalar(stmt)
    assert found is not None
    assert found.id == admin_user.id


async def test_email_переиспользуется_после_мягкого_удаления(
    session: AsyncSession,
    tenant: Tenant,
) -> None:
    """Ради этого уникальный индекс сделан частичным.

    Строка уволенного сотрудника физически остаётся в таблице. Будь индекс
    полным, его адрес был бы занят навсегда.
    """
    email = f"reused-{uuid.uuid4().hex[:8]}@example.com"

    first = User(tenant_id=tenant.id, name="Уволенный", email=email, permissions=["admin"])
    session.add(first)
    await session.commit()

    first.deleted_at = datetime.now(UTC)
    await session.commit()

    session.add(User(tenant_id=tenant.id, name="Новый", email=email, permissions=["admin"]))
    await session.commit()  # не должно нарушить уникальность


async def test_нельзя_создать_пользователя_с_недопустимым_статусом(
    session: AsyncSession,
    tenant: Tenant,
) -> None:
    """CHECK-ограничение в базе, а не только тип-аннотация в коде."""
    session.add(
        User(
            tenant_id=tenant.id,
            name="Кто-то",
            email=f"bad-status-{uuid.uuid4().hex[:8]}@example.com",
            permissions=["admin"],
            status="pending",  # состояния из прототипа здесь нет
        )
    )
    with pytest.raises(IntegrityError):
        await session.commit()
