"""Глобальный фильтр мягко удалённых записей — аналог `paranoid: true` из Sequelize.

В SQLAlchemy нет встроенного мягкого удаления, поэтому фильтр навешивается
слушателем события `do_orm_execute`: он добавляет `WHERE deleted_at IS NULL` в
каждый ORM-SELECT по модели с `SoftDeleteMixin`.

Это невидимая магия, поэтому важно знать две вещи:

1. Фильтр применяется и к eager-подгруженным связям (`include_aliases=True`),
   то есть `selectinload(Tenant.users)` тоже не вернёт удалённых.
2. Отключается на конкретном запросе:

       stmt = select(User).execution_options(include_deleted=True)

   Это аналог `paranoid: false` у отдельного запроса Sequelize. Нужен там, где
   удалённые записи как раз и требуются: админские отчёты, восстановление.

ВАЖНО: мультитенантность так НЕ делается. Соблазнительно повесить сюда второй
критерий, подставляющий `tenant_id` из contextvar, — но фоновые задачи
легитимно ходят между тенантами, и фильтр, который в одном пути кода молча
применяется, а в другом нет, опаснее отсутствия фильтра. `tenant_id`
передаётся в сервисы явным аргументом и попадает в каждый запрос явным
`.where()`. Гарантия — интеграционные тесты «не видит чужой тенант».
"""

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import ORMExecuteState, Session, with_loader_criteria

from saleslift.db.base import SoftDeleteMixin

#: Имя опции, отключающей фильтр на конкретном запросе.
INCLUDE_DELETED_OPTION = "include_deleted"


@event.listens_for(Session, "do_orm_execute")
def _apply_soft_delete_filter(state: ORMExecuteState) -> None:
    """Добавляет `deleted_at IS NULL` в каждый ORM-SELECT по soft-delete модели."""
    if not state.is_select:
        return

    # Дозагрузка колонки или связи у уже полученного объекта: критерий сюда
    # применять нельзя — объект уже в сессии, и фильтр только сломал бы
    # подгрузку его же собственных данных.
    if state.is_column_load or state.is_relationship_load:
        return

    if state.execution_options.get(INCLUDE_DELETED_OPTION, False):
        return

    state.statement = state.statement.options(
        with_loader_criteria(
            SoftDeleteMixin,
            lambda cls: cls.deleted_at.is_(None),
            # Критерий распространяется и на eager-загружаемые связи.
            include_aliases=True,
        )
    )


def include_deleted() -> dict[str, Any]:
    """Опции запроса, отключающие фильтр мягкого удаления.

    Использование::

        stmt = select(User).execution_options(**include_deleted())
    """
    return {INCLUDE_DELETED_OPTION: True}
