"""Универсальный экран запроса: панель фильтров + кнопка «Выполнить» + таблица + экспорт."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import AppError
from app.services.acl import require_permission, use
from app.ui.crud.descriptor import FieldKind
from app.ui.crud.form_builder import is_blank, make_input, pk_of, read_input
from app.ui.queries.csv_export import export_to_csv
from app.ui.queries.result_model import ResultTableModel
from app.ui.widgets import GhostButton, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext
    from app.ui.queries.descriptor import QueryDescriptor

_log = logging.getLogger(__name__)


class QueryView(QWidget):
    """Экран одного запроса (фильтры → таблица результата)."""

    # ---- init ----
    def __init__(
        self,
        descriptor: QueryDescriptor,
        session: Session,
        ctx: AuthContext,
        parent: QWidget | None = None,
    ) -> None:
        """Создать вид. ``session`` живёт столько же, сколько и экран."""
        super().__init__(parent)
        self._descriptor = descriptor
        self._session = session
        self._ctx = ctx
        self._inputs: dict[str, QWidget] = {}
        self._table_model = ResultTableModel(descriptor.result_columns)
        self._table_view: QTableView
        self._run_btn: PrimaryButton
        self._export_btn: SecondaryButton
        self._clear_btn: GhostButton
        self._total_label: QLabel
        self._error_label: QLabel
        self._build_ui()
        self._wire()

    # ---- slots ----
    @Slot()
    def _on_run(self) -> None:
        try:
            params = self._gather_params()
            with use(self._ctx):
                require_permission(self._descriptor.perm)
                rows = self._descriptor.runner(self._session, params)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._show_error(str(exc))
            self._table_model.set_rows([])
            self._update_total()
            return
        except Exception as exc:
            self._session.rollback()
            _log.exception("Ошибка выполнения запроса %s", self._descriptor.key)
            self._show_error(f"Ошибка выполнения: {exc}")
            self._table_model.set_rows([])
            self._update_total()
            return

        self._table_model.set_rows(rows)
        self._update_total()
        self._clear_error()

    @Slot()
    def _on_clear(self) -> None:
        for field in self._descriptor.params:
            widget = self._inputs[field.name]
            # Сброс на дефолты: проще пересоздать input и подменить.
            new_widget = make_input(field, self._session)
            layout: QFormLayout = self._form_layout
            layout.replaceWidget(widget, new_widget)
            widget.deleteLater()
            self._inputs[field.name] = new_widget
        self._table_model.set_rows([])
        self._update_total()
        self._clear_error()

    @Slot()
    def _on_export(self) -> None:
        if self._table_model.row_count() == 0:
            self._show_error("Нет данных для экспорта. Сначала выполните запрос.")
            return
        default_name = f"{self._descriptor.key}.csv"
        path_str, _filter = QFileDialog.getSaveFileName(
            self, "Экспорт в CSV", default_name, "CSV files (*.csv)"
        )
        if not path_str:
            return
        try:
            rows = self._collect_displayed_rows()
            export_to_csv(Path(path_str), self._descriptor.result_columns, rows)
        except OSError as exc:
            self._show_error(f"Не удалось записать файл: {exc}")
            return
        self._show_info(f"Сохранено: {path_str}")

    # ---- private ----
    def _build_ui(self) -> None:  # noqa: PLR0915
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        title = QLabel(self._descriptor.title)
        title.setObjectName("H1")
        outer.addWidget(title)

        if self._descriptor.description:
            desc = QLabel(self._descriptor.description)
            desc.setObjectName("Muted")
            desc.setWordWrap(True)
            outer.addWidget(desc)

        # filter card
        filters = QFrame()
        filters.setObjectName("Card")
        filters_layout = QVBoxLayout(filters)
        filters_layout.setContentsMargins(16, 12, 16, 12)
        filters_layout.setSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(8)
        for field in self._descriptor.params:
            widget = make_input(field, self._session)
            self._inputs[field.name] = widget
            lbl = QLabel(field.label)
            lbl.setObjectName("FieldLabel")
            form.addRow(lbl, widget)
        if not self._descriptor.params:
            empty = QLabel("Запрос выполняется без параметров.")
            empty.setObjectName("Muted")
            form.addRow(empty)
        self._form_layout = form
        filters_layout.addLayout(form)
        outer.addWidget(filters)

        # toolbar
        toolbar = QHBoxLayout()
        self._run_btn = PrimaryButton("Выполнить")
        self._clear_btn = GhostButton("Сбросить фильтры")
        self._export_btn = SecondaryButton("Экспорт CSV")
        # «Общее число» из варианта — показываем в строке действий, не «под таблицей».
        self._total_label = QLabel("")
        self._total_label.setObjectName("Muted")
        toolbar.addWidget(self._run_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addWidget(self._total_label)
        toolbar.addStretch(1)
        toolbar.addWidget(self._export_btn)
        outer.addLayout(toolbar)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        outer.addWidget(self._error_label)

        # results table
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.verticalHeader().setVisible(False)
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        outer.addWidget(self._table_view, 1)

    def _wire(self) -> None:
        self._run_btn.clicked.connect(self._on_run)
        self._clear_btn.clicked.connect(self._on_clear)
        self._export_btn.clicked.connect(self._on_export)

    def _gather_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for field in self._descriptor.params:
            value = read_input(field, self._inputs[field.name])
            if is_blank(value):
                continue
            if field.kind == FieldKind.RELATION and value is not None:
                value = pk_of(value)
            params[field.name] = value
        return params

    def _collect_displayed_rows(self) -> list[dict[str, Any]]:
        # ResultTableModel хранит _rows приватно; читаем через индексы.
        rows: list[dict[str, Any]] = []
        for r in range(self._table_model.row_count()):
            row_dict: dict[str, Any] = {}
            for c, col in enumerate(self._descriptor.result_columns):
                value = self._table_model.data(
                    self._table_model.index(r, c), Qt.ItemDataRole.DisplayRole
                )
                # Восстановить «сырое» значение нельзя — берём то, что отобразилось.
                row_dict[col.key] = value if value != "—" else None
            rows.append(row_dict)
        return rows

    def _update_total(self) -> None:
        count = self._table_model.row_count()
        self._total_label.setText(f"Общее число: {count}" if count else "")

    def _show_error(self, message: str) -> None:
        self._error_label.setStyleSheet("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.style().polish(self._error_label)
        self._error_label.setText(message)

    def _show_info(self, message: str) -> None:
        self._error_label.setText(message)

    def _clear_error(self) -> None:
        self._error_label.clear()
