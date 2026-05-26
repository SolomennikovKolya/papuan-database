"""Сервисный режим: очистка доменных таблиц, посев демо-данных, экспорт дампа.

Все операции требуют права ``service.testdata``. Системные таблицы
(``app_user``, ``role``, ``permission``, ``audit_login``, ассоциации)
очисткой **не затрагиваются** — пользователи и роли остаются.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import text

from app.core.config import get_settings
from app.core.errors import AppError
from app.fixtures import demo as demo_fixture
from app.models.base import Base
from app.services.acl import require

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)

# Эти таблицы — системные (ACL/аудит). Очистка их не трогает.
_SYSTEM_TABLES: frozenset[str] = frozenset({
    "app_user",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "audit_login",
})


class MaintenanceError(AppError):
    """Ошибка сервисного режима (не нашли утилиту, dump упал, и т.п.)."""


@dataclass(frozen=True)
class SeedReport:
    """Сводка по посеву демо-данных."""

    already_seeded: bool
    created: dict[str, int]


@dataclass(frozen=True)
class DumpReport:
    """Сводка по экспорту дампа БД."""

    path: str
    size_bytes: int


def domain_tables() -> list[str]:
    """Список доменных таблиц в порядке, безопасном для удаления (от листьев к корню)."""
    return [t.name for t in reversed(Base.metadata.sorted_tables) if t.name not in _SYSTEM_TABLES]


class MaintenanceService:
    """Очистка доменных данных, посев фикстур, экспорт дампа БД."""

    def __init__(self, session: Session) -> None:
        """Привязать к открытой сессии."""
        self._session = session

    @require("service.testdata")
    def truncate_domain(self) -> dict[str, int]:
        """Удалить все строки из доменных таблиц (системные — не трогаем).

        Возвращает словарь ``{имя_таблицы: число_удалённых_строк}``.
        """
        deleted: dict[str, int] = {}
        try:
            for table in domain_tables():
                # Кавычки — потому что имена вроде "group" зарезервированы в SQL.
                result = self._session.execute(text(f'DELETE FROM "{table}"'))
                deleted[table] = result.rowcount or 0
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise MaintenanceError(f"Не удалось очистить таблицы: {exc}") from exc
        _log.info("truncate_domain: %s", deleted)
        return deleted

    @require("service.testdata")
    def seed_demo(self) -> SeedReport:
        """Засеять демо-данными (идемпотентно). Возвращает счётчики и флаг ``already_seeded``."""
        try:
            already = demo_fixture.is_seeded(self._session)
            if already:
                return SeedReport(already_seeded=True, created={})
            counts = demo_fixture.seed(self._session)
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise MaintenanceError(f"Посев данных не удался: {exc}") from exc
        _log.info("seed_demo: %s", counts)
        return SeedReport(already_seeded=False, created=counts)

    @require("service.testdata")
    def export_dump(self, target: Path) -> DumpReport:
        """Сделать дамп через ``pg_dump`` (только для PostgreSQL)."""
        settings = get_settings()
        if not settings.db_url.drivername.startswith("postgresql"):
            raise MaintenanceError(
                "Экспорт дампа доступен только для PostgreSQL "
                f"(текущий драйвер: {settings.db_url.drivername})."
            )
        pg_dump = shutil.which("pg_dump")
        if pg_dump is None:
            raise MaintenanceError(
                "Утилита `pg_dump` не найдена в PATH. "
                "Установите PostgreSQL client tools и попробуйте снова."
            )
        env = {
            **os.environ,
            "PGPASSWORD": settings.db_password.get_secret_value(),
        }
        cmd = [
            pg_dump,
            "-h",
            settings.db_host,
            "-p",
            str(settings.db_port),
            "-U",
            settings.db_user,
            "-d",
            settings.db_name,
            "-f",
            str(target),
        ]
        _log.info("Запускаем pg_dump → %s", target)
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError as exc:
            raise MaintenanceError(f"Не удалось запустить pg_dump: {exc}") from exc
        if result.returncode != 0:
            raise MaintenanceError(
                f"pg_dump завершился с кодом {result.returncode}: {result.stderr.strip()}"
            )
        return DumpReport(path=str(target), size_bytes=target.stat().st_size)
