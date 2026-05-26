"""Засев прав, системной роли superadmin и пользователя admin.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from argon2 import PasswordHasher

from app.core.config import get_settings

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


_ENTITIES = (
    "section",
    "section_head",
    "group",
    "person",
    "tourist",
    "trainer",
    "training_session",
    "attendance",
    "competition",
    "route",
    "trip",
)
_ACTIONS = ("read", "create", "update", "delete")
_EXTRA_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("admin.users", "Управление пользователями и ролями"),
    ("admin.roles", "Управление набором прав у ролей"),
    ("sql.execute", "Выполнение произвольного SQL (read-only)"),
    ("sql.execute_write", "Выполнение произвольного SQL c записью"),
    ("service.testdata", "Сервисный режим: очистка/посев данных"),
)


def upgrade() -> None:
    """Засеять справочник прав, роль superadmin и пользователя admin."""
    bind = op.get_bind()
    permission_codes: list[tuple[str, str]] = [
        (f"{entity}.{action}", f"{action.capitalize()} сущности {entity}")
        for entity in _ENTITIES
        for action in _ACTIONS
    ]
    permission_codes.extend(_EXTRA_PERMISSIONS)

    bind.execute(
        sa.text("INSERT INTO permission (code, description) VALUES (:code, :description)"),
        [{"code": c, "description": d} for c, d in permission_codes],
    )

    bind.execute(
        sa.text(
            "INSERT INTO role (name, description, is_system) "
            "VALUES ('superadmin', 'Системная роль с полным доступом', TRUE)"
        )
    )
    bind.execute(
        sa.text(
            "INSERT INTO role_permission (role_id, permission_id) "
            "SELECT r.id, p.id FROM role r CROSS JOIN permission p "
            "WHERE r.name = 'superadmin'"
        )
    )

    settings = get_settings()
    password_hash = PasswordHasher().hash(settings.app_default_admin_password.get_secret_value())
    bind.execute(
        sa.text(
            "INSERT INTO app_user (login, password_hash, is_active) "
            "VALUES ('admin', :hash, TRUE)"
        ),
        {"hash": password_hash},
    )
    bind.execute(
        sa.text(
            "INSERT INTO user_role (user_id, role_id) "
            "SELECT u.id, r.id FROM app_user u JOIN role r ON r.name = 'superadmin' "
            "WHERE u.login = 'admin'"
        )
    )


def downgrade() -> None:
    """Удалить пользователя admin, роль superadmin и все права."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM user_role WHERE user_id IN (SELECT id FROM app_user WHERE login = 'admin')"
        )
    )
    bind.execute(sa.text("DELETE FROM app_user WHERE login = 'admin'"))
    bind.execute(
        sa.text(
            "DELETE FROM role_permission WHERE role_id IN "
            "(SELECT id FROM role WHERE name = 'superadmin')"
        )
    )
    bind.execute(sa.text("DELETE FROM role WHERE name = 'superadmin'"))
    bind.execute(sa.text("DELETE FROM permission"))
