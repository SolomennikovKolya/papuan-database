"""Создание read-only пользователя БД для SQL-консоли.

Требует, чтобы пользователь, выполняющий миграцию, имел право CREATEROLE
(в дефолтном Postgres-контейнере у POSTGRES_USER оно есть — он superuser).

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-26
"""

from __future__ import annotations

import re

import sqlalchemy as sa
from alembic import op

from app.core.config import get_settings

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None

# CREATE ROLE / GRANT — это DDL: Postgres парсит SQL до подстановки
# параметров, поэтому ':pwd'/'%s' там не работают. Имена ролей и БД
# валидируем регуляркой, пароль — литералим со стандартным экранированием
# одинарных кавычек.
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _ident(name: str) -> str:
    if not _IDENT_RE.fullmatch(name):
        raise ValueError(f"Небезопасный идентификатор для DDL: {name!r}")
    return name


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    """Создать роль для read-only подключения и выдать ей SELECT."""
    settings = get_settings()
    ro_user = _ident(settings.db_readonly_user)
    db_name = _ident(settings.db_name)
    pwd = _literal(settings.db_readonly_password.get_secret_value())
    bind = op.get_bind()

    exists = bind.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = :name"), {"name": ro_user}
    ).scalar()

    if exists:
        bind.execute(sa.text(f"ALTER ROLE {ro_user} WITH LOGIN PASSWORD {pwd}"))
    else:
        bind.execute(sa.text(f"CREATE ROLE {ro_user} WITH LOGIN PASSWORD {pwd}"))

    bind.execute(sa.text(f"GRANT CONNECT ON DATABASE {db_name} TO {ro_user}"))
    bind.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {ro_user}"))
    bind.execute(sa.text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {ro_user}"))
    bind.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {ro_user}"
        )
    )


def downgrade() -> None:
    """Отозвать права и (если возможно) удалить роль."""
    settings = get_settings()
    ro_user = _ident(settings.db_readonly_user)
    db_name = _ident(settings.db_name)
    bind = op.get_bind()

    bind.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE SELECT ON TABLES FROM {ro_user}"
        )
    )
    bind.execute(sa.text(f"REVOKE SELECT ON ALL TABLES IN SCHEMA public FROM {ro_user}"))
    bind.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {ro_user}"))
    bind.execute(sa.text(f"REVOKE CONNECT ON DATABASE {db_name} FROM {ro_user}"))
    bind.execute(sa.text(f"DROP ROLE IF EXISTS {ro_user}"))
