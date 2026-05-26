"""Дженерик-сервис CRUD над одной сущностью с проверкой прав.

Используется UI-слоем (``CrudView``) для **любой** доменной сущности. Имя
требуемого права собирается динамически из ``perm_prefix`` —
``"<entity>.<read|create|update|delete>"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.errors import ConflictError
from app.repositories import Page, Repository, Sort
from app.services.acl import require_permission

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session

    from app.models.base import Base


class EntityService[ModelT: Base]:
    """Тонкая обёртка над :class:`Repository` с ACL-проверками."""

    def __init__(self, session: Session, model: type[ModelT], perm_prefix: str) -> None:
        """Связать с сессией, моделью и префиксом прав (``"tourist"``, ``"route"``, …)."""
        self._session = session
        self._repo: Repository[ModelT] = Repository(session, model)
        self._prefix = perm_prefix

    def list(
        self,
        *,
        where: list[ColumnElement[bool]] | None = None,
        order_by: list[Sort] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[ModelT]:
        """Постраничный список сущностей. Требует ``<prefix>.read``."""
        require_permission(f"{self._prefix}.read")
        return self._repo.list(where=where, order_by=order_by, limit=limit, offset=offset)

    def get(self, pk: Any) -> ModelT:
        """Найти по PK или бросить :class:`~app.core.errors.NotFound`. Требует ``<prefix>.read``."""
        require_permission(f"{self._prefix}.read")
        return self._repo.get_or_raise(pk)

    def create(self, **fields: Any) -> ModelT:
        """Создать запись. Требует ``<prefix>.create``."""
        require_permission(f"{self._prefix}.create")
        try:
            return self._repo.create(**fields)
        except Exception as exc:
            self._session.rollback()
            raise self._wrap_integrity(exc) from exc

    def update(self, obj: ModelT, **changes: Any) -> ModelT:
        """Обновить запись. Требует ``<prefix>.update``."""
        require_permission(f"{self._prefix}.update")
        try:
            return self._repo.update(obj, **changes)
        except Exception as exc:
            self._session.rollback()
            raise self._wrap_integrity(exc) from exc

    def delete(self, obj: ModelT) -> None:
        """Удалить запись. Требует ``<prefix>.delete``."""
        require_permission(f"{self._prefix}.delete")
        try:
            self._repo.delete(obj)
        except Exception as exc:
            self._session.rollback()
            raise self._wrap_integrity(exc) from exc

    def _wrap_integrity(self, exc: Exception) -> Exception:
        """Переупаковать IntegrityError-ы в :class:`ConflictError` с понятным текстом."""
        msg = str(exc)
        if "FOREIGN KEY" in msg or "violates foreign key" in msg:
            return ConflictError(
                "Невозможно изменить или удалить: есть связанные записи в других таблицах."
            )
        if "UNIQUE" in msg or "duplicate key" in msg:
            return ConflictError("Нарушено ограничение уникальности (дубликат значения).")
        if "CHECK" in msg or "violates check" in msg:
            return ConflictError("Значение не проходит проверку допустимых значений.")
        return exc
