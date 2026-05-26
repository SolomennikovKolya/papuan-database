"""Окно входа в систему.

Принимает callable ``authenticate`` снаружи — не знает ни про БД, ни про
сервисы. Это упрощает тестирование (callable можно подменить) и держит
зависимости плоскими.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from app.core.errors import AuthenticationError
from app.ui.widgets import PrimaryButton

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtWidgets import QWidget

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)


class LoginWindow(QDialog):
    """Модальное окно входа.

    Сигнал :attr:`logged_in` — единственный публичный канал результата.
    Контроллер приложения подписывается на него и решает, что показывать
    дальше (обычно — скрыть это окно и поднять :class:`~app.ui.main_window.MainWindow`).
    """

    # ---- signals ----
    logged_in = Signal(object)  # payload: AuthContext

    # ---- init ----
    def __init__(
        self,
        authenticate: Callable[[str, str], AuthContext],
        parent: QWidget | None = None,
    ) -> None:
        """Создать окно.

        ``authenticate(login, password)`` бросает ``AuthenticationError`` при отказе.
        """
        super().__init__(parent)
        self._authenticate = authenticate
        self._login_edit: QLineEdit
        self._password_edit: QLineEdit
        self._error_label: QLabel
        self._submit_btn: PrimaryButton
        self.setWindowTitle("Tourist Club — вход")
        self.setMinimumWidth(380)
        self._build_ui()
        self._wire()

    # ---- public api ----
    def reset(self) -> None:
        """Очистить поля и состояние ошибки (используется при повторном показе после logout)."""
        self._password_edit.clear()
        self._error_label.clear()
        self._login_edit.setFocus()

    # ---- slots ----
    @Slot()
    def _on_submit(self) -> None:
        login = self._login_edit.text().strip()
        password = self._password_edit.text()
        if not login or not password:
            self._show_error("Введите логин и пароль")
            return

        self._set_busy(True)
        QApplication.processEvents()
        try:
            ctx = self._authenticate(login, password)
        except AuthenticationError as exc:
            self._show_error(str(exc))
        except Exception as exc:
            _log.exception("Системная ошибка при входе")
            self._show_error(f"Системная ошибка: {exc}")
        else:
            self.logged_in.emit(ctx)
            self.accept()
        finally:
            self._set_busy(False)

    # ---- private ----
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(16)

        title = QLabel("Tourist Club")
        title.setObjectName("H1")
        outer.addWidget(title)

        subtitle = QLabel("Информационная система туристического клуба")
        subtitle.setObjectName("Muted")
        outer.addWidget(subtitle)

        outer.addSpacing(8)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(8)

        self._login_edit = QLineEdit()
        self._login_edit.setPlaceholderText("admin")
        self._password_edit = QLineEdit()
        self._password_edit.setEchoMode(QLineEdit.EchoMode.Password)

        login_label = QLabel("Логин")
        login_label.setObjectName("FieldLabel")
        password_label = QLabel("Пароль")
        password_label.setObjectName("FieldLabel")

        form.addRow(login_label, self._login_edit)
        form.addRow(password_label, self._password_edit)
        outer.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        outer.addWidget(self._error_label)

        outer.addStretch(1)

        self._submit_btn = PrimaryButton("Войти")
        self._submit_btn.setDefault(True)
        outer.addWidget(self._submit_btn)

    def _wire(self) -> None:
        self._submit_btn.clicked.connect(self._on_submit)
        self._password_edit.returnPressed.connect(self._on_submit)
        self._login_edit.returnPressed.connect(self._password_edit.setFocus)

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)

    def _set_busy(self, busy: bool) -> None:
        self._submit_btn.setEnabled(not busy)
        self._submit_btn.setText("…проверяем…" if busy else "Войти")
        self._login_edit.setEnabled(not busy)
        self._password_edit.setEnabled(not busy)
