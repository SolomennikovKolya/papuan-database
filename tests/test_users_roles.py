"""Тесты сервисов администрирования: ``UsersService`` и ``RolesService``."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.core.errors import ConflictError, NotFound, PermissionDenied, ValidationError
from app.services import RolesService, UsersService, use
from app.services.acl import AuthContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from tests.conftest import SeededAcl


# ---------- UsersService ----------


class TestUsersServiceAccess:
    def test_create_without_permission_raises(
        self, session: Session, seeded_acl: SeededAcl
    ) -> None:
        weak_ctx = AuthContext(
            user_id=99, login="weak", is_superadmin=False, permissions=frozenset()
        )
        with use(weak_ctx), pytest.raises(PermissionDenied):
            UsersService(session).create("bob", "bobpass")

    def test_create_without_context_raises(self, session: Session, seeded_acl: SeededAcl) -> None:
        with pytest.raises(PermissionDenied):
            UsersService(session).create("bob", "bobpass")


class TestUsersServiceCreate:
    def test_create_user(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            user = UsersService(session).create("bob", "bobpass")
        assert user.id is not None
        assert user.login == "bob"
        assert user.is_active is True

    def test_duplicate_login_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            UsersService(session).create("bob", "bobpass")
            with pytest.raises(ConflictError, match="уже занят"):
                UsersService(session).create("bob", "anotherpass")

    def test_blank_login_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context), pytest.raises(ValidationError):
            UsersService(session).create("   ", "bobpass")

    def test_short_password_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context), pytest.raises(ValidationError):
            UsersService(session).create("bob", "ab")


class TestUsersServiceRoles:
    def test_assign_and_revoke_role(
        self, session: Session, admin_context: AuthContext, seeded_acl: SeededAcl
    ) -> None:
        with use(admin_context):
            svc = UsersService(session)
            user = svc.create("bob", "bobpass")
            svc.assign_role(user.id, seeded_acl.superadmin_role.id)
            assert seeded_acl.superadmin_role in user.roles
            svc.revoke_role(user.id, seeded_acl.superadmin_role.id)
            assert seeded_acl.superadmin_role not in user.roles

    def test_cannot_revoke_superadmin_from_builtin_admin(
        self, session: Session, admin_context: AuthContext, seeded_acl: SeededAcl
    ) -> None:
        with use(admin_context), pytest.raises(ConflictError, match="superadmin"):
            UsersService(session).revoke_role(
                seeded_acl.admin_user.id, seeded_acl.superadmin_role.id
            )

    def test_assign_unknown_role_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            user = UsersService(session).create("bob", "bobpass")
            with pytest.raises(NotFound):
                UsersService(session).assign_role(user.id, 9999)


class TestUsersServiceBlock:
    def test_block_builtin_admin_forbidden(
        self, session: Session, admin_context: AuthContext, seeded_acl: SeededAcl
    ) -> None:
        with use(admin_context), pytest.raises(ConflictError):
            UsersService(session).set_active(seeded_acl.admin_user.id, False)

    def test_block_regular_user_ok(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            svc = UsersService(session)
            user = svc.create("bob", "bobpass")
            svc.set_active(user.id, False)
            assert user.is_active is False


# ---------- RolesService ----------


class TestRolesService:
    def test_create_role(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            role = RolesService(session).create("editor", "Редакторы")
        assert role.id is not None
        assert role.is_system is False

    def test_cannot_delete_system_role(
        self, session: Session, admin_context: AuthContext, seeded_acl: SeededAcl
    ) -> None:
        with use(admin_context), pytest.raises(ConflictError, match=r"(?i)системн"):
            RolesService(session).delete(seeded_acl.superadmin_role.id)

    def test_cannot_modify_system_role_permissions(
        self, session: Session, admin_context: AuthContext, seeded_acl: SeededAcl
    ) -> None:
        with use(admin_context), pytest.raises(ConflictError):
            RolesService(session).set_permissions(seeded_acl.superadmin_role.id, [])

    def test_set_permissions_replaces(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            svc = RolesService(session)
            role = svc.create("editor")
            svc.set_permissions(role.id, ["tourist.read", "tourist.create"])
            assert {p.code for p in role.permissions} == {"tourist.read", "tourist.create"}
            svc.set_permissions(role.id, ["tourist.read"])
            assert {p.code for p in role.permissions} == {"tourist.read"}

    def test_unknown_permission_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            svc = RolesService(session)
            role = svc.create("editor")
            with pytest.raises(NotFound, match="bogus"):
                svc.set_permissions(role.id, ["bogus.right"])

    def test_duplicate_name_raises(self, session: Session, admin_context: AuthContext) -> None:
        with use(admin_context):
            svc = RolesService(session)
            svc.create("editor")
            with pytest.raises(ConflictError):
                svc.create("editor")
