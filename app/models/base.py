"""Базовый класс для ORM-моделей и общие типовые алиасы."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, mapped_column

# Единая naming convention для constraint-ов — Alembic корректно генерирует имена
# при autogenerate, а ручные миграции получают предсказуемые DROP-ы.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовый ORM-класс. Все модели наследуются от него."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# Удобный алиас для типизированных колонок timestamp-with-tz.
TimestampTz = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now()),
]
