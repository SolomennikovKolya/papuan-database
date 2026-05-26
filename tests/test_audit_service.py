"""Тесты ``AuditService``: фильтры журнала входов, ACL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.core.errors import PermissionDenied
from app.models import AuditLogin
from app.services import AuditService, use
from app.services.acl import AuthContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _ctx_admin() -> AuthContext:
    return AuthContext(user_id=1, login="admin", is_superadmin=True, permissions=frozenset())


def _seed(session: Session) -> None:
    now = datetime.now(UTC)
    rows = [
        ("admin", True, now),
        ("admin", False, now - timedelta(minutes=1)),
        ("bob", True, now - timedelta(minutes=2)),
        ("eve", False, now - timedelta(minutes=3)),
        ("eve", False, now - timedelta(minutes=4)),
    ]
    for login, success, ts in rows:
        session.add(AuditLogin(user_id=None, login_attempted=login, success=success, event_at=ts))
    session.commit()


class TestAuditServiceFilters:
    def test_recent_returns_descending(self, session: Session) -> None:
        _seed(session)
        with use(_ctx_admin()):
            page = AuditService(session).recent(limit=10)
        assert page.total == 5
        logins = [e.login_attempted for e in page.items]
        # Свежее — впереди.
        assert logins[0] == "admin"
        assert logins[-1] == "eve"

    def test_filter_by_login(self, session: Session) -> None:
        _seed(session)
        with use(_ctx_admin()):
            page = AuditService(session).recent(login="eve")
        assert page.total == 2
        assert all(e.login_attempted == "eve" for e in page.items)

    def test_filter_by_success_yes(self, session: Session) -> None:
        _seed(session)
        with use(_ctx_admin()):
            page = AuditService(session).recent(success=True)
        assert page.total == 2

    def test_filter_by_success_no(self, session: Session) -> None:
        _seed(session)
        with use(_ctx_admin()):
            page = AuditService(session).recent(success=False)
        assert page.total == 3

    def test_count_matches_recent_total(self, session: Session) -> None:
        _seed(session)
        with use(_ctx_admin()):
            count_all = AuditService(session).count()
            count_eve = AuditService(session).count(login="eve")
        assert count_all == 5
        assert count_eve == 2


class TestAuditServicePermissions:
    def test_recent_requires_admin_users(self, session: Session) -> None:
        weak = AuthContext(user_id=99, login="weak", is_superadmin=False, permissions=frozenset())
        with use(weak), pytest.raises(PermissionDenied):
            AuditService(session).recent()
