"""Управление пользователями: создание, блокировка, сброс пароля, назначение ролей."""

from __future__ import annotations

from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from sqlalchemy import select

from app.core.errors import ConflictError, NotFound, ValidationError
from app.models import AppUser, Role
from app.repositories import Page, Repository, Sort
from app.services.acl import SUPERADMIN_ROLE, require

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_MIN_PASSWORD_LENGTH = 4
_BUILTIN_ADMIN_LOGIN = "admin"


class UsersService:
    """Администрирование учётных записей. Все методы требуют права ``admin.users``."""

    def __init__(self, session: Session) -> None:
        """Привязать сервис к открытой сессии."""
        self._session = session
        self._repo = Repository(session, AppUser)
        self._hasher = PasswordHasher()

    @require("admin.users")
    def list(self, *, limit: int = 50, offset: int = 0) -> Page[AppUser]:
        """Постраничный список пользователей, отсортированный по логину."""
        return self._repo.list(limit=limit, offset=offset, order_by=[Sort("login")])

    @require("admin.users")
    def create(
        self,
        login: str,
        password: str,
        *,
        role_ids: list[int] | None = None,
        person_id: int | None = None,
    ) -> AppUser:
        """Создать пользователя; опционально назначить роли и связать с физлицом."""
        self._validate_login(login)
        self._validate_password(password)
        if self._login_taken(login):
            raise ConflictError(f"Логин {login!r} уже занят")

        user = self._repo.create(
            login=login,
            password_hash=self._hasher.hash(password),
            is_active=True,
            person_id=person_id,
        )
        if role_ids:
            for role_id in role_ids:
                user.roles.append(self._load_role(role_id))
            self._session.flush()
        return user

    @require("admin.users")
    def set_active(self, user_id: int, active: bool) -> AppUser:
        """Заблокировать или разблокировать пользователя (кроме встроенного ``admin``)."""
        user = self._repo.get_or_raise(user_id)
        if user.login == _BUILTIN_ADMIN_LOGIN and not active:
            raise ConflictError("Нельзя заблокировать встроенного пользователя admin")
        user.is_active = active
        self._session.flush()
        return user

    @require("admin.users")
    def reset_password(self, user_id: int, new_password: str) -> None:
        """Принудительно сменить пароль пользователя."""
        self._validate_password(new_password)
        user = self._repo.get_or_raise(user_id)
        user.password_hash = self._hasher.hash(new_password)
        self._session.flush()

    @require("admin.users")
    def assign_role(self, user_id: int, role_id: int) -> None:
        """Назначить пользователю роль (идемпотентно)."""
        user = self._repo.get_or_raise(user_id)
        role = self._load_role(role_id)
        if role not in user.roles:
            user.roles.append(role)
            self._session.flush()

    @require("admin.users")
    def revoke_role(self, user_id: int, role_id: int) -> None:
        """Снять у пользователя роль (с защитой встроенного admin от потери superadmin)."""
        user = self._repo.get_or_raise(user_id)
        role = self._load_role(role_id)
        if user.login == _BUILTIN_ADMIN_LOGIN and role.name == SUPERADMIN_ROLE:
            raise ConflictError("Нельзя снять роль superadmin со встроенного admin")
        if role in user.roles:
            user.roles.remove(role)
            self._session.flush()

    def _validate_login(self, login: str) -> None:
        if not login or not login.strip():
            raise ValidationError("Логин не может быть пустым")

    def _validate_password(self, password: str) -> None:
        if len(password) < _MIN_PASSWORD_LENGTH:
            raise ValidationError(f"Пароль должен быть не короче {_MIN_PASSWORD_LENGTH} символов")

    def _login_taken(self, login: str) -> bool:
        existing = self._session.execute(select(AppUser.id).where(AppUser.login == login)).first()
        return existing is not None

    def _load_role(self, role_id: int) -> Role:
        role = self._session.get(Role, role_id)
        if role is None:
            raise NotFound(f"Роль id={role_id} не найдена")
        return role
