"""Экран SQL-консоли: редактор → результат + история, RO/RW режимы."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import PermissionDenied
from app.services.acl import require_permission, use
from app.services.sql_console import SqlExecutionError
from app.ui.queries.csv_export import export_to_csv
from app.ui.queries.descriptor import ResultColumn
from app.ui.queries.result_model import ResultTableModel
from app.ui.widgets import GhostButton, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from app.core.query_history import QueryHistory
    from app.services.acl import AuthContext
    from app.services.sql_console import SqlConsoleService, SqlResult

_log = logging.getLogger(__name__)


class SqlConsoleView(QWidget):
    """Экран произвольного SQL: редактор, результат, история, переключатель режима."""

    # ---- init ----
    def __init__(
        self,
        service: SqlConsoleService,
        history: QueryHistory,
        ctx: AuthContext,
        parent: QWidget | None = None,
    ) -> None:
        """Принять готовый сервис исполнения, историю и контекст пользователя."""
        super().__init__(parent)
        self._service = service
        self._history = history
        self._ctx = ctx
        self._mode = "readonly"
        self._last_columns: list[ResultColumn] = []
        self._last_rows: list[dict] = []

        self._editor: QPlainTextEdit
        self._mode_group: QButtonGroup
        self._mode_label: QLabel
        self._history_combo: QComboBox
        self._run_btn: PrimaryButton
        self._commit_btn: SecondaryButton
        self._rollback_btn: SecondaryButton
        self._clear_btn: GhostButton
        self._export_btn: SecondaryButton
        self._status_label: QLabel
        self._result_stack: QStackedWidget
        self._result_table: QTableView
        self._result_model: ResultTableModel
        self._message_label: QLabel

        self._build_ui()
        self._wire()
        self._refresh_history_combo()
        self._update_button_states()

    # ---- public api ----
    def shutdown(self) -> None:
        """Корректно завершить — откатить незакрытую транзакцию."""
        self._service.close()

    # ---- slots ----
    @Slot()
    def _on_run(self) -> None:
        sql = self._editor.toPlainText().strip()
        if not sql:
            self._show_message("Введите SQL-запрос.", error=True)
            return
        try:
            with use(self._ctx):
                require_permission("sql.execute")
            result = self._service.execute(sql, readonly=(self._mode == "readonly"))
        except PermissionDenied as exc:
            self._show_message(str(exc), error=True)
            return
        except SqlExecutionError as exc:
            self._show_message(str(exc), error=True)
            self._update_button_states()
            return

        self._history.add(sql, self._mode)
        self._refresh_history_combo()
        self._render_result(result)
        self._update_button_states()

    @Slot()
    def _on_commit(self) -> None:
        try:
            self._service.commit_pending()
        except SqlExecutionError as exc:
            self._show_message(f"COMMIT не удался: {exc}", error=True)
            return
        self._show_message("Транзакция зафиксирована (COMMIT).")
        self._update_button_states()

    @Slot()
    def _on_rollback(self) -> None:
        self._service.rollback_pending()
        self._show_message("Транзакция отменена (ROLLBACK).")
        self._update_button_states()

    @Slot()
    def _on_mode_changed(self) -> None:
        new_mode = "full" if self._mode_group.checkedId() == 1 else "readonly"
        if new_mode == self._mode:
            return
        if self._service.has_pending:
            self._service.rollback_pending()
            self._show_message("Незавершённая транзакция отменена при смене режима.", error=False)
        self._mode = new_mode
        self._update_mode_label()
        self._update_button_states()

    @Slot(int)
    def _on_history_pick(self, index: int) -> None:
        if index <= 0:
            return
        entry = self._history.entries()[index - 1]
        self._editor.setPlainText(entry.sql)
        self._history_combo.setCurrentIndex(0)

    @Slot()
    def _on_clear_editor(self) -> None:
        self._editor.clear()
        self._editor.setFocus()

    @Slot()
    def _on_clear_history(self) -> None:
        confirm = QMessageBox.question(
            self,
            "Очистить историю?",
            "Удалить все сохранённые запросы из истории?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._history.clear()
            self._refresh_history_combo()

    @Slot()
    def _on_export(self) -> None:
        if not self._last_rows:
            self._show_message("Нет данных для экспорта.", error=True)
            return
        default_name = "sql_result.csv"
        path_str, _filter = QFileDialog.getSaveFileName(
            self, "Экспорт CSV", default_name, "CSV files (*.csv)"
        )
        if not path_str:
            return
        try:
            export_to_csv(Path(path_str), self._last_columns, self._last_rows)
        except OSError as exc:
            self._show_message(f"Не удалось записать файл: {exc}", error=True)
            return
        self._show_message(f"Сохранено: {path_str}")

    # ---- private ----
    def _build_ui(self) -> None:  # noqa: PLR0915
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        title = QLabel("SQL-консоль")
        title.setObjectName("H1")
        outer.addWidget(title)

        # mode bar
        mode_bar = QHBoxLayout()
        self._mode_group = QButtonGroup(self)
        ro_btn = QPushButton("Только чтение")
        ro_btn.setObjectName("SecondaryButton")
        ro_btn.setCheckable(True)
        ro_btn.setChecked(True)
        ro_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        full_btn = QPushButton("Полный доступ (RW)")
        full_btn.setObjectName("SecondaryButton")
        full_btn.setCheckable(True)
        full_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_group.addButton(ro_btn, 0)
        self._mode_group.addButton(full_btn, 1)
        mode_bar.addWidget(ro_btn)
        mode_bar.addWidget(full_btn)

        self._mode_label = QLabel("")
        self._mode_label.setObjectName("Muted")
        mode_bar.addWidget(self._mode_label, 1)

        # history dropdown
        history_label = QLabel("История:")
        history_label.setObjectName("FieldLabel")
        mode_bar.addWidget(history_label)
        self._history_combo = QComboBox()
        self._history_combo.setMinimumWidth(240)
        mode_bar.addWidget(self._history_combo)

        clear_history_btn = GhostButton("Очистить")
        mode_bar.addWidget(clear_history_btn)
        self._clear_history_btn = clear_history_btn

        outer.addLayout(mode_bar)

        # editor — фиксированная по высоте область, не растягивается (иначе при
        # сжатии окна нижние кнопки наезжали на поле ввода).
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("-- введите SQL и нажмите «Выполнить» (Ctrl+Enter)")
        font = QFont("Consolas, 'Cascadia Mono', monospace")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(11)
        self._editor.setFont(font)
        self._editor.setMinimumHeight(140)
        self._editor.setMaximumHeight(240)
        outer.addWidget(self._editor, 0)

        # action toolbar
        toolbar = QHBoxLayout()
        self._run_btn = PrimaryButton("Выполнить")
        self._commit_btn = SecondaryButton("Применить (COMMIT)")
        self._rollback_btn = SecondaryButton("Откатить (ROLLBACK)")
        self._clear_btn = GhostButton("Очистить редактор")
        self._export_btn = SecondaryButton("Экспорт CSV")
        toolbar.addWidget(self._run_btn)
        toolbar.addWidget(self._commit_btn)
        toolbar.addWidget(self._rollback_btn)
        toolbar.addWidget(self._clear_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self._export_btn)
        outer.addLayout(toolbar)

        # status / message
        self._status_label = QLabel("")
        self._status_label.setObjectName("Muted")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        # result area: stack between table and message
        self._result_model = ResultTableModel([])
        self._result_table = QTableView()
        self._result_table.setModel(self._result_model)
        self._result_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._result_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._result_table.setAlternatingRowColors(True)
        self._result_table.verticalHeader().setVisible(False)
        header = self._result_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)

        self._message_label = QLabel("")
        self._message_label.setObjectName("Muted")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._result_stack = QStackedWidget()
        self._result_stack.addWidget(self._result_table)
        self._result_stack.addWidget(self._message_label)
        outer.addWidget(self._result_stack, 1)

        self._update_mode_label()

    def _wire(self) -> None:
        self._run_btn.clicked.connect(self._on_run)
        self._commit_btn.clicked.connect(self._on_commit)
        self._rollback_btn.clicked.connect(self._on_rollback)
        self._clear_btn.clicked.connect(self._on_clear_editor)
        self._export_btn.clicked.connect(self._on_export)
        self._mode_group.idToggled.connect(lambda _id, _on: self._on_mode_changed())
        self._history_combo.currentIndexChanged.connect(self._on_history_pick)
        self._clear_history_btn.clicked.connect(self._on_clear_history)
        QShortcut(QKeySequence("Ctrl+Return"), self._editor, activated=self._on_run)
        QShortcut(QKeySequence("Ctrl+Enter"), self._editor, activated=self._on_run)

    def _update_mode_label(self) -> None:
        if self._mode == "readonly":
            self._mode_label.setText("режим: только чтение, изменения невозможны")
        else:
            self._mode_label.setText("режим: запись разрешена — будьте осторожны")

    def _update_button_states(self) -> None:
        pending = self._service.has_pending
        self._commit_btn.setEnabled(pending)
        self._rollback_btn.setEnabled(pending)
        # commit/rollback вообще скрываются в read-only — там их не будет.
        self._commit_btn.setVisible(self._mode == "full")
        self._rollback_btn.setVisible(self._mode == "full")
        self._export_btn.setEnabled(bool(self._last_rows))

    def _refresh_history_combo(self) -> None:
        max_preview = 80
        self._history_combo.blockSignals(True)
        self._history_combo.clear()
        self._history_combo.addItem("— выбрать запрос —")
        for entry in self._history.entries():
            preview = entry.sql.replace("\n", " ").strip()
            if len(preview) > max_preview:
                preview = preview[:max_preview] + "…"
            tag = "[full]" if entry.mode == "full" else "[ro]"
            self._history_combo.addItem(f"{tag} {preview}")
        self._history_combo.blockSignals(False)

    def _render_result(self, result: SqlResult) -> None:
        if result.returns_rows:
            columns = [ResultColumn(key=name, title=name) for name in result.columns]
            rows = [dict(zip(result.columns, row, strict=False)) for row in result.rows]
            self._last_columns = columns
            self._last_rows = rows
            self._result_model = ResultTableModel(columns)
            self._result_model.set_rows(rows)
            self._result_table.setModel(self._result_model)
            self._result_stack.setCurrentWidget(self._result_table)
            self._status_label.setText(
                f"Возвращено строк: {result.rowcount} · {result.elapsed_ms} мс · {result.notice}"
            )
        else:
            self._last_columns = []
            self._last_rows = []
            self._result_model.set_rows([])
            self._message_label.setText(
                f"Запрос выполнен.\nЗатронуто строк: {result.rowcount}\n{result.notice}"
            )
            self._result_stack.setCurrentWidget(self._message_label)
            self._status_label.setText(f"{result.elapsed_ms} мс · {result.notice}")

    def _show_message(self, text_: str, *, error: bool = False) -> None:
        prefix = "Ошибка: " if error else ""
        self._status_label.setText(prefix + text_)
        if error:
            self._message_label.setText(prefix + text_)
            self._result_stack.setCurrentWidget(self._message_label)
