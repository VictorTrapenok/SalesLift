"""Фоновая задача — одновременно очередь и трекер прогресса."""

import uuid
from datetime import datetime
from typing import Any, Literal, get_args

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, Uuid, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from saleslift.db.base import Base, SoftDeleteMixin, TimestampMixin, UuidPkMixin

#: Состояние задачи.
#:   - `pending` — ждёт исполнителя;
#:   - `running` — захвачена воркером (`worker_id`, `locked_at` заполнены);
#:   - `done`    — успешно завершена;
#:   - `failed`  — исчерпаны попытки, подробности в `error_details`.
BackgroundTaskStatus = Literal["pending", "running", "done", "failed"]
BACKGROUND_TASK_STATUSES: tuple[str, ...] = get_args(BackgroundTaskStatus)


class BackgroundTask(UuidPkMixin, TimestampMixin, SoftDeleteMixin, Base):
    """Задача, исполняемая воркером асинхронно.

    Очередь живёт в PostgreSQL, а не в Redis: это осознанный размен. Плюс —
    в кластере не нужен ещё один stateful-компонент, и установка остаётся
    одной командой. Минус — нет fan-out и sub-секундной задержки; для
    транскрибации и анализа звонков, где задача идёт минуты, это неважно.

    Захват задачи — `SELECT ... FOR UPDATE SKIP LOCKED`: несколько воркеров
    могут разбирать очередь параллельно, не блокируя друг друга и не рискуя
    взять одну задачу дважды (см. `services/tasks/background_task_service.py`).

    Семантика доставки — at-least-once: воркер может умереть после выполнения
    работы, но до отметки `done`, и тогда задача будет исполнена повторно.
    Обработчики обязаны быть идемпотентны.
    """

    __tablename__ = "background_tasks"
    __table_args__ = (
        # Частичный индекс ровно под запрос захвата: планировщик ищет
        # `status='pending'` в порядке created_at. Индекс покрывает только
        # ждущие задачи, поэтому не растёт вместе с историей выполненных.
        Index(
            "ix_background_tasks_claim",
            "created_at",
            postgresql_where=text("status = 'pending' AND deleted_at IS NULL"),
        ),
        # Имя без префикса таблицы: его добавит шаблон из naming_convention.
        CheckConstraint(
            f"status IN ({', '.join(repr(s) for s in BACKGROUND_TASK_STATUSES)})",
            name="status",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )

    #: Сотрудник, инициировавший задачу: ему показывается прогресс.
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    #: Имя обработчика — по нему воркер выбирает, что исполнять.
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    #: Человекочитаемое описание для интерфейса.
    description: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="pending")

    #: Входные данные обработчика. В прототипе этого поля не было: там
    #: background_tasks только отображала прогресс, а очередью служила
    #: отдельная таблица. Здесь таблица одна, поэтому payload обязателен.
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    # ── Прогресс ─────────────────────────────────────────────────────────
    #: Текущий шаг словами — показывается в интерфейсе.
    current_task: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    #: Произвольные данные обработчика (промежуточные результаты, ссылки).
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default="{}")

    #: Подробности последней ошибки. NULL, если задача не падала.
    error_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    #: Номер попытки, начиная с 1. Увеличивается при возврате зависшей задачи
    #: в очередь (см. джоб stale_task_recovery).
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")

    #: Идентификатор захватившего воркера. Без внешнего ключа: таблицы
    #: воркеров нет, значение живёт только на время жизни процесса.
    worker_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    #: Момент захвата. По нему джоб восстановления находит зависшие задачи.
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<BackgroundTask id={self.id} name={self.name!r} status={self.status}>"
