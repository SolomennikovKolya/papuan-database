"""Тесты :class:`AuthService`: успешный/неуспешный логин, лог, блокировка."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.core.errors import AuthenticationError
from app.models import AppUser, AuditLogin
from app.services.auth import AuthService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.conftest import SeededAcl

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "adminpass"


class TestAuthenticate:
    def test_success_returns_context_with_permissions(
        self, session: Session, seeded_acl: SeededAcl
    ) -> None:
        ctx = AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)
        assert ctx.user_id == seeded_acl.admin_user.id
        assert ctx.login == ADMIN_LOGIN
        assert ctx.is_superadmin is True
        assert "admin.users" in ctx.permissions

    def test_success_updates_last_login(self, session: Session, seeded_acl: SeededAcl) -> None:
        before = datetime.now(UTC).replace(tzinfo=None)
        AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)
        session.refresh(seeded_acl.admin_user)
        recorded = seeded_acl.admin_user.last_successful_login_at
        assert recorded is not None
        # SQLite возвращает naive datetime, Postgres — aware; нормализуем к naive.
        recorded_naive = recorded.replace(tzinfo=None)
        assert recorded_naive >= before

    def test_wrong_password_raises(self, session: Session, seeded_acl: SeededAcl) -> None:
        with pytest.raises(AuthenticationError, match="Неверный"):
            AuthService(session).authenticate(ADMIN_LOGIN, "totally-wrong")

    def test_unknown_login_raises(self, session: Session, seeded_acl: SeededAcl) -> None:
        with pytest.raises(AuthenticationError, match="Неверный"):
            AuthService(session).authenticate("nosuchuser", "whatever")

    def test_inactive_user_raises(self, session: Session, seeded_acl: SeededAcl) -> None:
        seeded_acl.admin_user.is_active = False
        session.flush()
        with pytest.raises(AuthenticationError, match="заблокирована"):
            AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)


class TestAuditLog:
    def _count_audits(self, session: Session, login: str) -> int:
        return len(
            list(
                session.execute(
                    select(AuditLogin).where(AuditLogin.login_attempted == login)
                ).scalars()
            )
        )

    def test_success_records_audit(self, session: Session, seeded_acl: SeededAcl) -> None:
        AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)
        session.flush()
        entries = list(
            session.execute(
                select(AuditLogin).where(AuditLogin.login_attempted == ADMIN_LOGIN)
            ).scalars()
        )
        assert any(e.success for e in entries)

    def test_failure_records_audit(self, session: Session, seeded_acl: SeededAcl) -> None:
        with pytest.raises(AuthenticationError):
            AuthService(session).authenticate(ADMIN_LOGIN, "wrong")
        session.flush()
        entries = list(
            session.execute(
                select(AuditLogin).where(AuditLogin.login_attempted == ADMIN_LOGIN)
            ).scalars()
        )
        assert any(not e.success for e in entries)


class TestLockout:
    def _seed_failed_attempts(self, session: Session, login: str, count: int) -> None:
        now = datetime.now(UTC)
        for i in range(count):
            session.add(
                AuditLogin(
                    user_id=None,
                    login_attempted=login,
                    event_at=now - timedelta(seconds=i),
                    success=False,
                )
            )
        session.commit()

    def test_lockout_after_max_failures(self, session: Session, seeded_acl: SeededAcl) -> None:
        self._seed_failed_attempts(session, ADMIN_LOGIN, AuthService.MAX_FAILURES)
        with pytest.raises(AuthenticationError, match="неудачных"):
            AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)

    def test_old_failures_do_not_lock(self, session: Session, seeded_acl: SeededAcl) -> None:
        old_time = datetime.now(UTC) - timedelta(hours=1)
        for _ in range(AuthService.MAX_FAILURES):
            session.add(
                AuditLogin(
                    user_id=None,
                    login_attempted=ADMIN_LOGIN,
                    event_at=old_time,
                    success=False,
                )
            )
        session.commit()
        ctx = AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)
        assert ctx.user_id == seeded_acl.admin_user.id


class TestChangePassword:
    def test_change_password_invalidates_old(self, session: Session, seeded_acl: SeededAcl) -> None:
        svc = AuthService(session)
        svc.change_password(seeded_acl.admin_user, "newpassword")
        session.flush()

        with pytest.raises(AuthenticationError):
            AuthService(session).authenticate(ADMIN_LOGIN, ADMIN_PASSWORD)

        ctx = AuthService(session).authenticate(ADMIN_LOGIN, "newpassword")
        assert ctx.login == ADMIN_LOGIN


def test_audit_login_user_id_set_on_known_login(session: Session, seeded_acl: SeededAcl) -> None:
    """Если логин существует, неудача всё равно должна привязать audit к user_id."""
    with pytest.raises(AuthenticationError):
        AuthService(session).authenticate(ADMIN_LOGIN, "wrong")
    session.flush()
    user = session.execute(select(AppUser).where(AppUser.login == ADMIN_LOGIN)).scalar_one()
    entry = (
        session
        .execute(
            select(AuditLogin)
            .where(AuditLogin.user_id == user.id, AuditLogin.success.is_(False))
            .order_by(AuditLogin.id.desc())
        )
        .scalars()
        .first()
    )
    assert entry is not None
