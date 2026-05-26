"""Тесты ACL: контекст текущего пользователя и декоратор ``@require``."""

from __future__ import annotations

import pytest

from app.core.errors import PermissionDenied
from app.services.acl import AuthContext, current, require, require_current, use


def _ctx(*permissions: str, is_superadmin: bool = False) -> AuthContext:
    return AuthContext(
        user_id=1,
        login="tester",
        is_superadmin=is_superadmin,
        permissions=frozenset(permissions),
    )


class TestHas:
    def test_user_with_permission(self) -> None:
        assert _ctx("tourist.read").has("tourist.read")

    def test_user_without_permission(self) -> None:
        assert not _ctx("tourist.read").has("tourist.delete")

    def test_superadmin_has_anything(self) -> None:
        assert _ctx(is_superadmin=True).has("any.permission.here")


class TestContextVar:
    def test_no_user_by_default(self) -> None:
        assert current() is None

    def test_use_sets_and_restores(self) -> None:
        ctx = _ctx("x")
        with use(ctx):
            assert current() is ctx
        assert current() is None

    def test_use_nesting(self) -> None:
        outer = _ctx("a")
        inner = _ctx("b")
        with use(outer):
            with use(inner):
                assert current() is inner
            assert current() is outer

    def test_require_current_without_user_raises(self) -> None:
        with pytest.raises(PermissionDenied):
            require_current()


class TestRequireDecorator:
    def test_without_context_raises(self) -> None:
        @require("tourist.delete")
        def fn() -> str:
            return "ok"

        with pytest.raises(PermissionDenied):
            fn()

    def test_without_permission_raises(self) -> None:
        @require("tourist.delete")
        def fn() -> str:
            return "ok"

        with use(_ctx("tourist.read")), pytest.raises(PermissionDenied, match=r"tourist\.delete"):
            fn()

    def test_with_permission_passes_through(self) -> None:
        @require("tourist.delete")
        def fn(x: int) -> int:
            return x * 2

        with use(_ctx("tourist.delete")):
            assert fn(5) == 10

    def test_superadmin_bypasses(self) -> None:
        @require("anything.write")
        def fn() -> str:
            return "ok"

        with use(_ctx(is_superadmin=True)):
            assert fn() == "ok"
