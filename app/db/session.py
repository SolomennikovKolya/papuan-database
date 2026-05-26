"""Управление сессиями SQLAlchemy.

Используем контекстный менеджер :func:`session_scope` как **единственную**
точку открытия транзакции. Он гарантирует commit при успехе и rollback при
исключении. Сервисный слой принимает уже открытую сессию вторым аргументом
или открывает свою через ``session_scope``.
"""

from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, sessionmaker

from app.db.engine import get_engine

if TYPE_CHECKING:
    from collections.abc import Iterator


@lru_cache(maxsize=1)
def _session_factory() -> sessionmaker[Session]:
    """Вернуть закэшированную фабрику сессий, привязанную к основному движку."""
    return sessionmaker(
        bind=get_engine(),
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )


@contextmanager
def session_scope() -> Iterator[Session]:
    """Открыть транзакционную сессию.

    Commit выполняется автоматически при успешном выходе из блока, rollback —
    при любом исключении. Сессия всегда закрывается.
    """
    session = _session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
