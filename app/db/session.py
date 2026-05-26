"""Управление сессиями SQLAlchemy.

В большинстве случаев каллер использует контекстный менеджер
:func:`session_scope` — он гарантирует commit при успехе и rollback при
исключении. Когда поведение «commit в любом случае» обязательно (например,
:class:`~app.services.auth.AuthService.authenticate`, который должен сохранить
запись аудита даже при ``AuthenticationError``), берётся «голая» сессия
через :func:`new_session` и закрывается каллером вручную.
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


def new_session() -> Session:
    """Открыть новую сессию (каллер сам решает, когда commit/rollback/close)."""
    return _session_factory()()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Открыть транзакционную сессию.

    Commit выполняется автоматически при успешном выходе из блока, rollback —
    при любом исключении. Сессия всегда закрывается.
    """
    session = new_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
