"""Объединённый раздел «Консоль»: готовые запросы по варианту + произвольный SQL."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from app.core.query_history import QueryHistory
from app.db.engine import get_engine, get_readonly_engine
from app.services.sql_console import SqlConsoleService
from app.ui.queries.page import QueriesPage
from app.ui.sql_console import SqlConsoleView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext


class ConsolePage(QWidget):
    """Tabs: «Готовые запросы» и «SQL»."""

    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст пользователя; SQL-вкладка зависит от ``sql.execute``."""
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.addTab(QueriesPage(session, ctx), "Готовые запросы")

        if ctx.has("sql.execute"):
            service = SqlConsoleService(rw_engine=get_engine(), ro_engine=get_readonly_engine())
            history = QueryHistory()
            tabs.addTab(SqlConsoleView(service=service, history=history, ctx=ctx), "SQL")
        else:
            denied = QWidget()
            d_layout = QVBoxLayout(denied)
            d_layout.setContentsMargins(32, 32, 32, 32)
            label = QLabel("Для выполнения произвольного SQL требуется право `sql.execute`.")
            label.setObjectName("Muted")
            d_layout.addWidget(label)
            d_layout.addStretch(1)
            tabs.addTab(denied, "SQL")
            tabs.setTabEnabled(1, False)

        layout.addWidget(tabs)
