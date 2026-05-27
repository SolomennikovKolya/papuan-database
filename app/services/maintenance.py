"""Сервисный режим: очистка доменных таблиц, посев демо-данных, экспорт дампа.

Все операции требуют права ``service.testdata``. Очистка удаляет все доменные
данные, а также пользователей и роли — **кроме** встроенного ``admin`` и
системной роли ``superadmin`` (иначе в систему было бы не войти). Справочник
прав (``permission``) и журнал входов (``audit_login``) сохраняются.
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
from app.services.acl import SUPERADMIN_ROLE, require

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)

# Эти таблицы очисткой не трогаем напрямую в общем цикле:
# - permission/audit_login сохраняются полностью;
# - app_user/role чистятся отдельно, с сохранением admin/superadmin;
# - role_permission/user_role подчищаются каскадом по FK.
_SYSTEM_TABLES: frozenset[str] = frozenset({
    "app_user",
    "role",
    "permission",
    "role_permission",
    "user_role",
    "audit_login",
})

# Встроенные учётка и роль, которые очистка обязана сохранить.
_BUILTIN_ADMIN_LOGIN = "admin"


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
        """Удалить все доменные данные + пользователей/роли (кроме admin/superadmin).

        Справочник прав и журнал входов сохраняются. Возвращает словарь
        ``{имя_таблицы: число_удалённых_строк}``.
        """
        deleted: dict[str, int] = {}
        try:
            for table in domain_tables():
                # Кавычки — потому что имена вроде "group" зарезервированы в SQL.
                result = self._session.execute(text(f'DELETE FROM "{table}"'))
                deleted[table] = result.rowcount or 0

            # Пользователи и роли — кроме встроенных admin / superadmin.
            # Связки чистим явно (не полагаясь на ON DELETE CASCADE — на SQLite
            # он по умолчанию выключен, и остались бы «осиротевшие» строки).
            self._session.execute(
                text(
                    "DELETE FROM user_role WHERE user_id IN "
                    "(SELECT id FROM app_user WHERE login <> :login)"
                ),
                {"login": _BUILTIN_ADMIN_LOGIN},
            )
            self._session.execute(
                text(
                    "DELETE FROM role_permission WHERE role_id IN "
                    "(SELECT id FROM role WHERE name <> :name)"
                ),
                {"name": SUPERADMIN_ROLE},
            )
            users = self._session.execute(
                text("DELETE FROM app_user WHERE login <> :login"),
                {"login": _BUILTIN_ADMIN_LOGIN},
            )
            deleted["app_user"] = users.rowcount or 0
            roles = self._session.execute(
                text("DELETE FROM role WHERE name <> :name"),
                {"name": SUPERADMIN_ROLE},
            )
            deleted["role"] = roles.rowcount or 0

            self._session.commit()
            # Сбросить identity map, чтобы ORM не держал удалённые объекты.
            self._session.expire_all()
        except Exception as exc:
            self._session.rollback()
            raise MaintenanceError(f"Не удалось очистить таблицы: {exc}") from exc
        _log.info("truncate_domain: %s", deleted)
        return deleted

    @require("service.testdata")
    def seed_demo(self) -> SeedReport:
        """Засеять демо-данными (идемпотентно): доменные данные + роли + пользователи.

        Доменная часть создаётся только на пустой БД; роли и пользователи —
        идемпотентно (по имени/логину). Так посев полностью определяет рабочую
        БД и безопасен к повторному вызову. ``already_seeded`` истинно, только
        если не создано вообще ничего.
        """
        try:
            counts = demo_fixture.seed(self._session)
            counts.update(demo_fixture.seed_access(self._session))
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            raise MaintenanceError(f"Посев данных не удался: {exc}") from exc
        _log.info("seed_demo: %s", counts)
        return SeedReport(already_seeded=not counts, created=counts)

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
