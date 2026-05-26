"""Тесты ``EntityService``: проверка прав и упаковка ошибок целостности."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from app.core.errors import ConflictError, NotFound, PermissionDenied
from app.models import Difficulty
from app.services import EntityService, use
from app.services.acl import AuthContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _ctx(*permissions: str) -> AuthContext:
    return AuthContext(
        user_id=1, login="t", is_superadmin=False, permissions=frozenset(permissions)
    )


def _row(code: str, sort_order: int) -> dict[str, object]:
    return {
        "code": code,
        "name": f"Категория {code}",
        "min_length_km": Decimal("10"),
        "min_days": 1,
        "sort_order": sort_order,
    }


class TestPermissionChecks:
    def test_list_requires_read(self, session: Session) -> None:
        svc: EntityService = EntityService(session, Difficulty, "tourist")
        with use(_ctx()), pytest.raises(PermissionDenied):
            svc.list()

    def test_create_requires_create(self, session: Session) -> None:
        svc: EntityService = EntityService(session, Difficulty, "tourist")
        with use(_ctx("tourist.read")), pytest.raises(PermissionDenied):
            svc.create(**_row("I", 1))

    def test_with_correct_permission_passes(self, session: Session) -> None:
        svc: EntityService = EntityService(session, Difficulty, "tourist")
        with use(_ctx("tourist.read", "tourist.create")):
            obj = svc.create(**_row("II", 2))
        assert obj.id is not None


class TestIntegrityWrapping:
    def test_unique_violation_becomes_conflict(self, session: Session) -> None:
        svc: EntityService = EntityService(session, Difficulty, "tourist")
        with use(_ctx("tourist.read", "tourist.create")):
            svc.create(**_row("III", 3))
            session.commit()
            with pytest.raises(ConflictError, match="уникальности"):
                svc.create(**_row("III", 4))  # duplicate code

    def test_get_missing_raises_not_found(self, session: Session) -> None:
        svc: EntityService = EntityService(session, Difficulty, "tourist")
        with use(_ctx("tourist.read")), pytest.raises(NotFound):
            svc.get(9999)
