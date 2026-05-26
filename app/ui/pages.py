"""Страницы главного окна: справочники, тренировки, походы.

Каждая страница — контейнер с левым списком сущностей и :class:`CrudView`
справа. Список сущностей собирается из :mod:`app.ui.descriptors`,
а ленивое создание CrudView (только когда нужно) экономит DB-запросы.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.crud import CrudView

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext
    from app.ui.crud import EntityDescriptor


class EntityListPage(QWidget):
    """Sidebar-список сущностей + ленивое создание ``CrudView`` справа."""

    # ---- init ----
    def __init__(
        self,
        descriptors: list[EntityDescriptor],
        session: Session,
        ctx: AuthContext,
        parent: QWidget | None = None,
    ) -> None:
        """Принять список описаний сущностей; CrudView создаются лениво при первом показе."""
        super().__init__(parent)
        self._descriptors = [d for d in descriptors if ctx.has(f"{d.perm_prefix}.read")]
        self._session = session
        self._ctx = ctx
        self._views: dict[int, CrudView] = {}
        self._list: QListWidget
        self._stack: QStackedWidget
        self._build_ui()
        self._wire()
        if self._descriptors:
            self._list.setCurrentRow(0)

    # ---- private ----
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not self._descriptors:
            empty = QWidget()
            empty_layout = QVBoxLayout(empty)
            empty_layout.setContentsMargins(32, 32, 32, 32)
            label = QLabel("Нет доступных сущностей.\nОбратитесь к администратору.")
            label.setObjectName("Muted")
            empty_layout.addWidget(label)
            empty_layout.addStretch(1)
            layout.addWidget(empty, 1)
            self._list = QListWidget()  # пустой, чтобы атрибут существовал
            self._stack = QStackedWidget()
            return

        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(220)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setObjectName("EntityList")
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)
        for descriptor in self._descriptors:
            QListWidgetItem(descriptor.title, self._list)
        side_layout.addWidget(self._list, 1)
        layout.addWidget(side)

        self._stack = QStackedWidget()
        for _ in self._descriptors:
            self._stack.addWidget(QWidget())  # placeholder, заменяется при первом клике
        layout.addWidget(self._stack, 1)

    def _wire(self) -> None:
        if self._descriptors:
            self._list.currentRowChanged.connect(self._on_row_changed)

    # ---- slots ----
    @Slot(int)
    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._descriptors):
            return
        if row not in self._views:
            view = CrudView(self._descriptors[row], self._session, self._ctx)
            self._views[row] = view
            placeholder = self._stack.widget(row)
            self._stack.removeWidget(placeholder)
            self._stack.insertWidget(row, view)
            placeholder.deleteLater()
        self._stack.setCurrentIndex(row)


def make_placeholder(title: str, hint: str) -> QWidget:
    """Заглушка для разделов, которые наполняются на следующих этапах."""
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(32, 32, 32, 32)
    layout.setSpacing(8)
    h1 = QLabel(title)
    h1.setObjectName("H1")
    layout.addWidget(h1)
    muted = QLabel(hint)
    muted.setObjectName("Muted")
    muted.setWordWrap(True)
    layout.addWidget(muted)
    layout.addStretch(1)
    return page
