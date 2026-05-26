"""Пользователи, роли, права, аудит — таблицы ACL."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.people import Person


class AppUser(Base):
    """Пользователь приложения (для аутентификации в GUI)."""

    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
    person_id: Mapped[int | None] = mapped_column(ForeignKey("person.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_successful_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person | None] = relationship()
    roles: Mapped[list[Role]] = relationship(secondary="user_role", back_populates="users")


class Role(Base):
    """Роль в системе ACL. Системные роли (`is_system=True`) не редактируются."""

    __tablename__ = "role"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(default=False, server_default="false")

    users: Mapped[list[AppUser]] = relationship(secondary="user_role", back_populates="roles")
    permissions: Mapped[list[Permission]] = relationship(
        secondary="role_permission", back_populates="roles"
    )


class Permission(Base):
    """Атомарное право (например, ``tourist.read``, ``sql.execute``)."""

    __tablename__ = "permission"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))

    roles: Mapped[list[Role]] = relationship(
        secondary="role_permission", back_populates="permissions"
    )


class RolePermission(Base):
    """Связь роль ↔ право."""

    __tablename__ = "role_permission"

    role_id: Mapped[int] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permission.id", ondelete="CASCADE"), primary_key=True
    )


class UserRole(Base):
    """Связь пользователь ↔ роль."""

    __tablename__ = "user_role"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("app_user.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("role.id", ondelete="CASCADE"), primary_key=True
    )


class AuditLogin(Base):
    """Журнал попыток входа (успешных и неуспешных)."""

    __tablename__ = "audit_login"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("app_user.id", ondelete="SET NULL"))
    login_attempted: Mapped[str] = mapped_column(String(80))
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    success: Mapped[bool]
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(255))
