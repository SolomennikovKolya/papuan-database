"""Тесты ``MaintenanceService``: truncate, seed (идемпотентный), export-precheck."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.core.errors import PermissionDenied
from app.models import (
    AppUser,
    AuditLogin,
    Difficulty,
    Permission,
    Person,
    Role,
    Section,
    SectionHead,
)
from app.services import MaintenanceService, use
from app.services.acl import AuthContext
from app.services.maintenance import MaintenanceError, domain_tables

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.orm import Session

    from tests.conftest import SeededAcl


_ADMIN_CTX = AuthContext(user_id=1, login="admin", is_superadmin=True, permissions=frozenset())


class TestDomainTables:
    def test_excludes_system_tables(self) -> None:
        names = domain_tables()
        for system in (
            "app_user",
            "role",
            "permission",
            "role_permission",
            "user_role",
            "audit_login",
        ):
            assert system not in names, f"{system!r} попало в список доменных"

    def test_includes_main_domain_tables(self) -> None:
        names = set(domain_tables())
        for required in ("person", "section", "trip", "training_session", "tourist"):
            assert required in names


class TestSeed:
    def test_seed_creates_data(self, session: Session) -> None:
        with use(_ADMIN_CTX):
            report = MaintenanceService(session).seed_demo()
        assert report.already_seeded is False
        assert report.created["section"] >= 1
        assert session.execute(select(Section)).first() is not None

    def test_seed_is_idempotent(self, session: Session) -> None:
        with use(_ADMIN_CTX):
            svc = MaintenanceService(session)
            first = svc.seed_demo()
            second = svc.seed_demo()
        assert first.already_seeded is False
        assert second.already_seeded is True
        assert second.created == {}

    def test_seed_creates_roles_and_users(self, session: Session) -> None:
        with use(_ADMIN_CTX):
            MaintenanceService(session).seed_demo()
        role_names = {r.name for r in session.execute(select(Role)).scalars()}
        assert {"Менеджер данных", "Аналитик", "Тренер"} <= role_names
        logins = {u.login for u in session.execute(select(AppUser)).scalars()}
        assert {"manager", "analyst", "coach"} <= logins

    def test_seed_access_idempotent_after_truncate(self, session: Session) -> None:
        # Повторный посев после очистки доменных данных не дублирует роли/учётки.
        with use(_ADMIN_CTX):
            svc = MaintenanceService(session)
            svc.seed_demo()
            svc.truncate_domain()
            svc.seed_demo()
        stmt = select(AppUser).where(AppUser.login == "manager")
        managers = list(session.execute(stmt).scalars())
        assert len(managers) == 1


class TestTruncate:
    def test_truncate_removes_domain_data(self, session: Session, seeded_acl: SeededAcl) -> None:
        with use(_ADMIN_CTX):
            MaintenanceService(session).seed_demo()
            assert session.execute(select(Person)).first() is not None
            MaintenanceService(session).truncate_domain()
        assert session.execute(select(Person)).first() is None
        assert session.execute(select(Section)).first() is None
        assert session.execute(select(SectionHead)).first() is None
        assert session.execute(select(Difficulty)).first() is None

    def test_truncate_keeps_acl_and_audit(self, session: Session, seeded_acl: SeededAcl) -> None:
        # AuditLogin запись для эффекта
        session.add(AuditLogin(user_id=None, login_attempted="x", success=False))
        session.commit()

        with use(_ADMIN_CTX):
            MaintenanceService(session).truncate_domain()

        # Встроенные admin/superadmin, права и журнал не пострадали:
        assert session.execute(select(AppUser).where(AppUser.login == "admin")).first()
        assert session.execute(select(Role).where(Role.name == "superadmin")).first()
        assert session.execute(select(Permission)).first() is not None
        assert session.execute(select(AuditLogin)).first() is not None

    def test_truncate_removes_non_builtin_users_and_roles(
        self, session: Session, seeded_acl: SeededAcl
    ) -> None:
        with use(_ADMIN_CTX):
            MaintenanceService(session).seed_demo()  # создаёт демо-роли и учётки
            MaintenanceService(session).truncate_domain()
        logins = {u.login for u in session.execute(select(AppUser)).scalars()}
        role_names = {r.name for r in session.execute(select(Role)).scalars()}
        # Демо-учётки и роли удалены, встроенные остались.
        assert logins == {"admin"}
        assert role_names == {"superadmin"}


class TestExport:
    def test_export_requires_postgres(self, session: Session, tmp_path: Path) -> None:
        # Settings.db_url по умолчанию указывает на postgresql; но проверим
        # фактическое поведение через перехват MaintenanceError для случая,
        # когда pg_dump недоступен или БД — не Postgres.
        # На тестовой машине pg_dump может быть или не быть — обе ветки приемлемы.
        try:
            with use(_ADMIN_CTX), pytest.raises(MaintenanceError):
                MaintenanceService(session).export_dump(tmp_path / "dump.sql")
        except PermissionDenied:
            pytest.fail("Должно бросать MaintenanceError, не PermissionDenied")


class TestPermissions:
    def test_truncate_requires_service_testdata(self, session: Session) -> None:
        weak = AuthContext(user_id=99, login="weak", is_superadmin=False, permissions=frozenset())
        with use(weak), pytest.raises(PermissionDenied):
            MaintenanceService(session).truncate_domain()

    def test_seed_requires_service_testdata(self, session: Session) -> None:
        weak = AuthContext(user_id=99, login="weak", is_superadmin=False, permissions=frozenset())
        with use(weak), pytest.raises(PermissionDenied):
            MaintenanceService(session).seed_demo()
