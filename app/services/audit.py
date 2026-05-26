"""Сервис чтения журнала входов (``audit_login``).

Записывать события туда умеет :class:`~app.services.auth.AuthService`;
этот сервис нужен только админ-панели для просмотра.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models import AuditLogin
from app.repositories import Page, Repository, Sort
from app.services.acl import require

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class AuditService:
    """Чтение журнала входов. Все методы требуют права ``admin.users``."""

    def __init__(self, session: Session) -> None:
        """Привязать сервис к открытой сессии."""
        self._session = session
        self._repo: Repository[AuditLogin] = Repository(session, AuditLogin)

    @require("admin.users")
    def recent(
        self,
        *,
        login: str | None = None,
        success: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Page[AuditLogin]:
        """Постраничный журнал входов с опциональными фильтрами."""
        where = []
        if login:
            where.append(AuditLogin.login_attempted.ilike(f"%{login}%"))
        if success is not None:
            where.append(AuditLogin.success.is_(success))
        return self._repo.list(
            where=where,
            order_by=[Sort("event_at", descending=True)],
            limit=limit,
            offset=offset,
        )

    @require("admin.users")
    def count(self, *, login: str | None = None, success: bool | None = None) -> int:
        """Полное число записей по фильтру (для пагинатора)."""
        stmt = select(AuditLogin.id)
        if login:
            stmt = stmt.where(AuditLogin.login_attempted.ilike(f"%{login}%"))
        if success is not None:
            stmt = stmt.where(AuditLogin.success.is_(success))
        return len(list(self._session.execute(stmt).all()))
