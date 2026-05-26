"""Управление ролями и набором их прав."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.core.errors import ConflictError, NotFound, ValidationError
from app.models import Permission, Role
from app.repositories import Page, Repository, Sort
from app.services.acl import require

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class RolesService:
    """Администрирование ролей. Все методы требуют права ``admin.roles``."""

    def __init__(self, session: Session) -> None:
        """Привязать сервис к открытой сессии."""
        self._session = session
        self._repo = Repository(session, Role)

    @require("admin.roles")
    def list(self) -> Page[Role]:
        """Все роли в алфавитном порядке."""
        return self._repo.list(order_by=[Sort("name")])

    @require("admin.roles")
    def create(self, name: str, description: str | None = None) -> Role:
        """Создать пользовательскую роль (не системную)."""
        self._validate_name(name)
        if self._name_taken(name):
            raise ConflictError(f"Роль с именем {name!r} уже существует")
        return self._repo.create(name=name, description=description, is_system=False)

    @require("admin.roles")
    def rename(self, role_id: int, *, name: str, description: str | None) -> Role:
        """Переименовать роль / поправить описание (только пользовательские)."""
        role = self._repo.get_or_raise(role_id)
        self._guard_not_system(role)
        self._validate_name(name)
        if name != role.name and self._name_taken(name):
            raise ConflictError(f"Роль с именем {name!r} уже существует")
        role.name = name
        role.description = description
        self._session.flush()
        return role

    @require("admin.roles")
    def delete(self, role_id: int) -> None:
        """Удалить роль (нельзя для системных)."""
        role = self._repo.get_or_raise(role_id)
        self._guard_not_system(role)
        self._repo.delete(role)

    @require("admin.roles")
    def set_permissions(self, role_id: int, permission_codes: list[str]) -> Role:
        """Полностью заменить набор прав у роли (для системной — запрещено)."""
        role = self._repo.get_or_raise(role_id)
        self._guard_not_system(role)
        if permission_codes:
            permissions = list(
                self._session.execute(
                    select(Permission).where(Permission.code.in_(permission_codes))
                ).scalars()
            )
            missing = set(permission_codes) - {p.code for p in permissions}
            if missing:
                raise NotFound(f"Неизвестные права: {sorted(missing)}")
        else:
            permissions = []
        role.permissions = permissions
        self._session.flush()
        return role

    def _validate_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValidationError("Имя роли не может быть пустым")

    def _name_taken(self, name: str) -> bool:
        return self._session.execute(select(Role.id).where(Role.name == name)).first() is not None

    def _guard_not_system(self, role: Role) -> None:
        if role.is_system:
            raise ConflictError(f"Системную роль {role.name!r} нельзя изменять")
