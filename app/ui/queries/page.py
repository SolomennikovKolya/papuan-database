"""Страница «Запросы по варианту»: sidebar со списком + стек QueryView-ов."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.queries.descriptors import ALL_QUERIES
from app.ui.queries.query_view import QueryView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext


class QueriesPage(QWidget):
    """Слева — список 13 запросов; справа — ленивый ``QueryView``."""

    # ---- init ----
    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст; запросы создаются при первом клике."""
        super().__init__(parent)
        self._descriptors = [d for d in ALL_QUERIES if ctx.has(d.perm)]
        self._session = session
        self._ctx = ctx
        self._views: dict[int, QueryView] = {}
        self._list: QListWidget
        self._stack: QStackedWidget
        self._build_ui()
        self._wire()
        if self._descriptors:
            self._list.setCurrentRow(0)

    # ---- slots ----
    @Slot(int)
    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._descriptors):
            return
        if row not in self._views:
            view = QueryView(self._descriptors[row], self._session, self._ctx)
            self._views[row] = view
            placeholder = self._stack.widget(row)
            self._stack.removeWidget(placeholder)
            self._stack.insertWidget(row, view)
            placeholder.deleteLater()
        self._stack.setCurrentIndex(row)

    # ---- private ----
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(280)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setObjectName("QueryList")
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)
        for descriptor in self._descriptors:
            QListWidgetItem(descriptor.title, self._list)
        side_layout.addWidget(self._list, 1)
        layout.addWidget(side)

        self._stack = QStackedWidget()
        for _ in self._descriptors:
            self._stack.addWidget(QWidget())
        layout.addWidget(self._stack, 1)

    def _wire(self) -> None:
        if self._descriptors:
            self._list.currentRowChanged.connect(self._on_row_changed)
