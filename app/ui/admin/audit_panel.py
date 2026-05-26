"""Панель журнала входов (audit_login) с фильтрами и пагинацией."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import AppError
from app.services import AuditService, use
from app.ui.crud.descriptor import Column
from app.ui.crud.table_model import EntityTableModel
from app.ui.widgets import GhostButton, PrimaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)

_PAGE_SIZE = 100


_COLUMNS: list[Column] = [
    Column("id", "ID", width=70, align="right"),
    Column("event_at", "Время", width=180),
    Column("login_attempted", "Логин"),
    Column(
        "success",
        "Успех",
        width=80,
        align="center",
        formatter=lambda v: "✓" if v else "✗",
    ),
    Column("user_id", "ID пользователя", width=140, align="right"),
    Column("ip_address", "IP"),
]


class AuditPanel(QWidget):
    """Список последних попыток входа + фильтр + пагинация."""

    # ---- init ----
    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст пользователя; список загружается сразу."""
        super().__init__(parent)
        self._session = session
        self._ctx = ctx
        self._svc = AuditService(session)
        self._model = EntityTableModel(_COLUMNS)
        self._offset = 0
        self._total = 0
        self._login_filter: QLineEdit
        self._success_filter: QComboBox
        self._refresh_btn: PrimaryButton
        self._prev_btn: GhostButton
        self._next_btn: GhostButton
        self._pager_label: QLabel
        self._table: QTableView
        self._error_label: QLabel
        self._build_ui()
        self._wire()
        self.refresh()

    # ---- public api ----
    def refresh(self) -> None:
        """Перечитать страницу журнала из БД с учётом текущих фильтров."""
        login_val = self._login_filter.text().strip() or None
        success_val: bool | None
        choice = self._success_filter.currentData()
        if choice == "yes":
            success_val = True
        elif choice == "no":
            success_val = False
        else:
            success_val = None
        try:
            with use(self._ctx):
                page = self._svc.recent(
                    login=login_val,
                    success=success_val,
                    limit=_PAGE_SIZE,
                    offset=self._offset,
                )
                self._total = self._svc.count(login=login_val, success=success_val)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._error_label.setText(str(exc))
            self._model.set_items([])
            self._total = 0
            self._update_pager()
            return
        self._model.set_items(list(page.items))
        self._update_pager()
        self._error_label.setText("")

    # ---- slots ----
    @Slot()
    def _on_filter_changed(self) -> None:
        self._offset = 0
        self.refresh()

    @Slot()
    def _on_prev(self) -> None:
        if self._offset == 0:
            return
        self._offset = max(0, self._offset - _PAGE_SIZE)
        self.refresh()

    @Slot()
    def _on_next(self) -> None:
        if self._offset + _PAGE_SIZE >= self._total:
            return
        self._offset += _PAGE_SIZE
        self.refresh()

    # ---- private ----
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Журнал входов")
        title.setObjectName("H2")
        layout.addWidget(title)

        filters = QHBoxLayout()
        login_lbl = QLabel("Логин:")
        login_lbl.setObjectName("FieldLabel")
        filters.addWidget(login_lbl)
        self._login_filter = QLineEdit()
        self._login_filter.setClearButtonEnabled(True)
        self._login_filter.setPlaceholderText("часть логина")
        self._login_filter.setMaximumWidth(240)
        filters.addWidget(self._login_filter)

        succ_lbl = QLabel("Результат:")
        succ_lbl.setObjectName("FieldLabel")
        filters.addWidget(succ_lbl)
        self._success_filter = QComboBox()
        self._success_filter.addItem("любой", None)
        self._success_filter.addItem("успех", "yes")
        self._success_filter.addItem("отказ", "no")
        filters.addWidget(self._success_filter)

        self._refresh_btn = PrimaryButton("Обновить")
        filters.addWidget(self._refresh_btn)
        filters.addStretch(1)
        layout.addLayout(filters)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        layout.addWidget(self._error_label)

        pager = QHBoxLayout()
        self._prev_btn = GhostButton("← Назад")
        self._next_btn = GhostButton("Вперёд →")
        self._pager_label = QLabel("")
        self._pager_label.setObjectName("Muted")
        pager.addWidget(self._prev_btn)
        pager.addWidget(self._pager_label, 1)
        pager.addWidget(self._next_btn)
        layout.addLayout(pager)

    def _wire(self) -> None:
        self._refresh_btn.clicked.connect(self.refresh)
        self._login_filter.returnPressed.connect(self._on_filter_changed)
        self._success_filter.currentIndexChanged.connect(self._on_filter_changed)
        self._prev_btn.clicked.connect(self._on_prev)
        self._next_btn.clicked.connect(self._on_next)

    def _update_pager(self) -> None:
        start = self._offset + 1 if self._total > 0 else 0
        end = min(self._offset + _PAGE_SIZE, self._total)
        self._pager_label.setText(f"{start}–{end} из {self._total}")
        self._prev_btn.setEnabled(self._offset > 0)
        self._next_btn.setEnabled(self._offset + _PAGE_SIZE < self._total)


__all__ = ["AuditPanel"]
