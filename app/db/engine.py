"""Создание SQLAlchemy-движков для основного и read-only подключений.

На один процесс — один основной движок и один read-only (создаются лениво
при первом обращении). Это безопасно, так как пул соединений у SQLAlchemy
сам по себе потокобезопасен.
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import Engine, create_engine

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Вернуть основной движок (под пользователем приложения, RW)."""
    settings = get_settings()
    return create_engine(
        settings.db_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_readonly_engine() -> Engine:
    """Вернуть read-only движок для SQL-консоли (см. спецификацию §5.4)."""
    settings = get_settings()
    return create_engine(
        settings.db_readonly_url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


def dispose_all() -> None:
    """Закрыть пул соединений всех закэшированных движков.

    Вызывается при штатном завершении приложения; в тестах — между прогонами.
    """
    for factory in (get_engine, get_readonly_engine):
        if factory.cache_info().currsize:
            factory().dispose()
        factory.cache_clear()
