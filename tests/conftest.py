"""Общие фикстуры pytest.

Для unit-тестов слоя данных поднимаем SQLite в памяти и накатываем
``Base.metadata`` — это даёт быстрый и изолированный движок без зависимости
от запущенного Postgres. Триггеры и Postgres-специфичные ограничения здесь
не проверяются (это уровень интеграционных тестов).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest
from argon2 import PasswordHasher
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import AppUser, Permission, Role
from app.models.base import Base
from app.services.acl import SUPERADMIN_ROLE, AuthContext

if TYPE_CHECKING:
    from collections.abc import Iterator

ADMIN_PASSWORD = "adminpass"
DEFAULT_PERMISSIONS = (
    "admin.users",
    "admin.roles",
    "sql.execute",
    "service.testdata",
    "tourist.read",
    "tourist.create",
)


@pytest.fixture
def session() -> Iterator[Session]:
    """Изолированная SQLAlchemy-сессия поверх свежей in-memory SQLite-базы."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


@dataclass
class SeededAcl:
    """Минимальный набор «адмиских» сущностей для тестов сервисов."""

    superadmin_role: Role
    admin_user: AppUser
    permissions: dict[str, Permission]


@pytest.fixture
def seeded_acl(session: Session) -> SeededAcl:
    """Засеять справочник прав, роль ``superadmin`` и пользователя ``admin``."""
    perms = {code: Permission(code=code, description=code) for code in DEFAULT_PERMISSIONS}
    session.add_all(perms.values())
    session.flush()

    role = Role(name=SUPERADMIN_ROLE, description="System superadmin", is_system=True)
    role.permissions = list(perms.values())
    session.add(role)
    session.flush()

    user = AppUser(
        login="admin",
        password_hash=PasswordHasher().hash(ADMIN_PASSWORD),
        is_active=True,
    )
    user.roles.append(role)
    session.add(user)
    session.commit()  # коммит для устойчивости тестов аудит-лога/блокировок
    return SeededAcl(superadmin_role=role, admin_user=user, permissions=perms)


@pytest.fixture
def admin_context(seeded_acl: SeededAcl) -> AuthContext:
    """Готовый :class:`AuthContext` для встроенного admin (для ``with use(...)``)."""
    return AuthContext(
        user_id=seeded_acl.admin_user.id,
        login=seeded_acl.admin_user.login,
        is_superadmin=True,
        permissions=frozenset(seeded_acl.permissions),
    )
