"""Общие фикстуры pytest.

Для unit-тестов слоя данных поднимаем SQLite в памяти и накатываем
``Base.metadata`` — это даёт быстрый и изолированный движок без зависимости
от запущенного Postgres. Триггеры и Postgres-специфичные ограничения здесь
не проверяются (это уровень интеграционных тестов).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.fixture
def session() -> Iterator[Session]:
    """Изолированная SQLAlchemy-сессия поверх свежей in-memory SQLite-базы."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()
