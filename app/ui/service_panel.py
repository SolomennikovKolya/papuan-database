"""Экран сервисного режима: очистка БД, посев демо-данных, экспорт дампа."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import AppError
from app.services import MaintenanceService, use
from app.ui.widgets import Card, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)


class ServicePanel(QWidget):
    """Кнопки сервисного режима: очистка/посев/экспорт + протокол операций."""

    # ---- init ----
    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст; команды защищены правом ``service.testdata``."""
        super().__init__(parent)
        self._session = session
        self._ctx = ctx
        self._svc = MaintenanceService(session)
        self._log: QLabel
        self._truncate_btn: SecondaryButton
        self._seed_btn: PrimaryButton
        self._dump_btn: SecondaryButton
        self._build_ui()
        self._wire()
        self._append_log("Готов к работе.")

    # ---- slots ----
    @Slot()
    def _on_truncate(self) -> None:
        first = QMessageBox.warning(
            self,
            "Очистка БД",
            "Это удалит все доменные данные (туристы, секции, походы и т.п.).\n"
            "Системные таблицы (пользователи, роли, журнал) не пострадают.\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if first != QMessageBox.StandardButton.Yes:
            return
        confirm = QMessageBox.critical(
            self,
            "Подтвердите ещё раз",
            "Действительно удалить ВСЕ доменные данные?\nОтменить будет нельзя.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            with use(self._ctx):
                deleted = self._svc.truncate_domain()
        except AppError as exc:
            self._append_log(f"❌ Очистка: {exc}")
            return
        total = sum(deleted.values())
        self._append_log(f"✓ Очистка завершена. Удалено строк: {total}.")

    @Slot()
    def _on_seed(self) -> None:
        try:
            with use(self._ctx):
                report = self._svc.seed_demo()
        except AppError as exc:
            self._append_log(f"❌ Посев: {exc}")
            return
        if report.already_seeded:
            self._append_log("⚠ В БД уже есть данные — посев пропущен. Сначала очистите БД.")
            return
        breakdown = ", ".join(f"{k}={v}" for k, v in report.created.items())
        self._append_log(f"✓ Демо-данные засеяны: {breakdown}")

    @Slot()
    def _on_export(self) -> None:
        suggested = f"tourist_club_{datetime.now():%Y%m%d_%H%M%S}.sql"
        path_str, _filter = QFileDialog.getSaveFileName(
            self, "Сохранить дамп", suggested, "SQL files (*.sql)"
        )
        if not path_str:
            return
        try:
            with use(self._ctx):
                report = self._svc.export_dump(Path(path_str))
        except AppError as exc:
            self._append_log(f"❌ Экспорт дампа: {exc}")
            return
        kib = max(1, report.size_bytes // 1024)
        self._append_log(f"✓ Дамп сохранён: {report.path} ({kib} КБ)")

    # ---- private ----
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        title = QLabel("Сервисный режим")
        title.setObjectName("H1")
        outer.addWidget(title)

        warning = QLabel(
            "Эти операции необратимы и затрагивают всю базу. Используйте с осторожностью."
        )
        warning.setObjectName("Muted")
        warning.setWordWrap(True)
        outer.addWidget(warning)

        outer.addWidget(
            self._make_action_card(
                "Очистить БД",
                "Удалить все доменные данные (туристы, секции, походы, тренировки и т.п.). "
                "Системные таблицы (пользователи, роли, журнал) остаются нетронутыми.",
                "Очистить",
                primary=False,
                slot_attr="_truncate_btn",
            )
        )

        outer.addWidget(
            self._make_action_card(
                "Засеять демо-данными",
                "Наполнить пустую БД заранее подготовленным набором "
                "(секции, тренеры, маршруты, походы, тренировки, соревнования). "
                "Если в БД уже есть данные — операция пропускается.",
                "Засеять",
                primary=True,
                slot_attr="_seed_btn",
            )
        )

        outer.addWidget(
            self._make_action_card(
                "Экспортировать дамп",
                "Создать .sql-файл всей БД через `pg_dump`. Требует установленных "
                "PostgreSQL client tools и подключения к PostgreSQL.",
                "Сохранить как…",
                primary=False,
                slot_attr="_dump_btn",
            )
        )

        log_label = QLabel("Протокол операций")
        log_label.setObjectName("H2")
        outer.addWidget(log_label)

        self._log = QLabel("")
        self._log.setObjectName("Muted")
        self._log.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._log.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._log.setWordWrap(True)
        log_card = Card()
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(16, 12, 16, 12)
        log_layout.addWidget(self._log)
        outer.addWidget(log_card, 1)

    def _make_action_card(
        self, title: str, description: str, button_text: str, *, primary: bool, slot_attr: str
    ) -> QFrame:
        card = Card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        text_box = QVBoxLayout()
        text_box.setSpacing(4)
        h = QLabel(title)
        h.setObjectName("H2")
        d = QLabel(description)
        d.setObjectName("Muted")
        d.setWordWrap(True)
        text_box.addWidget(h)
        text_box.addWidget(d)
        layout.addLayout(text_box, 1)

        btn: PrimaryButton | SecondaryButton
        btn = PrimaryButton(button_text) if primary else SecondaryButton(button_text)
        setattr(self, slot_attr, btn)
        layout.addWidget(btn, 0)
        return card

    def _wire(self) -> None:
        self._truncate_btn.clicked.connect(self._on_truncate)
        self._seed_btn.clicked.connect(self._on_seed)
        self._dump_btn.clicked.connect(self._on_export)

    def _append_log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        current = self._log.text()
        prefix = "" if not current else current + "\n"
        self._log.setText(prefix + f"[{ts}] {message}")
