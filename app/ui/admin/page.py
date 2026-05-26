"""Главная страница админ-панели: три вкладки в одном ``QTabWidget``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.ui.admin.audit_panel import AuditPanel
from app.ui.admin.roles_panel import RolesPanel
from app.ui.admin.users_panel import UsersPanel

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext


class AdminPage(QWidget):
    """Контейнер: ``Пользователи | Роли | Журнал входов``."""

    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять общую сессию и контекст; вкладки наследуют их."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(UsersPanel(session, ctx), "Пользователи")
        tabs.addTab(RolesPanel(session, ctx), "Роли")
        tabs.addTab(AuditPanel(session, ctx), "Журнал входов")
        layout.addWidget(tabs)
