"""Страницы главного окна: данные (с группировкой), консоль и заглушки."""

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


class DataPage(QWidget):
    """Список сущностей слева (с заголовками-группами) + ``CrudView`` справа."""

    # ---- init ----
    def __init__(
        self,
        groups: list[tuple[str, list[EntityDescriptor]]],
        session: Session,
        ctx: AuthContext,
        parent: QWidget | None = None,
    ) -> None:
        """Принять группы сущностей. Группы без доступных пунктов пропускаются."""
        super().__init__(parent)
        self._session = session
        self._ctx = ctx
        # Фильтрация по правам и формирование плоского массива (item_row → descriptor).
        self._rows: list[EntityDescriptor | None] = []  # None для заголовка-разделителя
        self._groups: list[tuple[str, list[EntityDescriptor]]] = []
        for title, descriptors in groups:
            visible = [d for d in descriptors if ctx.has(f"{d.perm_prefix}.read")]
            if visible:
                self._groups.append((title, visible))
        self._views: dict[int, CrudView] = {}
        self._list: QListWidget
        self._stack: QStackedWidget
        self._build_ui()
        self._wire()
        # Активировать первую «реальную» строку (после первого header-а).
        for i, item in enumerate(self._rows):
            if item is not None:
                self._list.setCurrentRow(i)
                break

    # ---- private ----
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if not self._groups:
            empty_layout = QVBoxLayout()
            empty_layout.setContentsMargins(32, 32, 32, 32)
            label = QLabel("Нет доступных сущностей.\nОбратитесь к администратору.")
            label.setObjectName("Muted")
            empty_layout.addWidget(label)
            empty_layout.addStretch(1)
            wrap = QWidget()
            wrap.setLayout(empty_layout)
            layout.addWidget(wrap, 1)
            self._list = QListWidget()
            self._stack = QStackedWidget()
            return

        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(240)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        self._list = QListWidget()
        self._list.setObjectName("GroupedList")
        self._list.setFrameShape(QListWidget.Shape.NoFrame)
        self._list.setCursor(Qt.CursorShape.PointingHandCursor)

        for title, descriptors in self._groups:
            header = QListWidgetItem(title.upper(), self._list)
            header.setFlags(Qt.ItemFlag.NoItemFlags)  # disabled, non-selectable
            self._rows.append(None)
            for d in descriptors:
                item = QListWidgetItem("  " + d.title, self._list)
                self._rows.append(d)

        side_layout.addWidget(self._list, 1)
        layout.addWidget(side)

        self._stack = QStackedWidget()
        for descriptor in self._rows:
            # Для header-ов — заглушка, для реальных — placeholder (lazy create).
            self._stack.addWidget(QWidget())
            _ = descriptor  # silence linter
        layout.addWidget(self._stack, 1)

    def _wire(self) -> None:
        if self._groups:
            self._list.currentRowChanged.connect(self._on_row_changed)

    # ---- slots ----
    @Slot(int)
    def _on_row_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._rows):
            return
        descriptor = self._rows[row]
        if descriptor is None:
            # Заголовок группы — игнорируем (но он и так non-selectable).
            return
        if row not in self._views:
            view = CrudView(descriptor, self._session, self._ctx)
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
