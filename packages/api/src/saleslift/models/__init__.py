"""Реестр ORM-моделей — единственный источник истины о составе схемы.

Список ЯВНЫЙ, автозагрузчика по маске файлов нет. От этого зависят две вещи:
  - `Base.metadata` знает обо всех таблицах, поэтому `alembic revision
    --autogenerate` видит их все, а не только импортированные по случайности;
  - маппер SQLAlchemy резолвит строковые ссылки в relationship (`"User"`).

При добавлении модели — добавь импорт сюда, иначе она будет работать до первой
миграции и молча отсутствовать в autogenerate. Подробности — в readme.md рядом.
"""

from saleslift.db.base import Base
from saleslift.models.background_task import BackgroundTask
from saleslift.models.tenant import Tenant
from saleslift.models.user import User

__all__ = [
    "BackgroundTask",
    "Base",
    "Tenant",
    "User",
]
