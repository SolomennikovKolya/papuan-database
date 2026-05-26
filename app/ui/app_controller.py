"""Оркестрация UI: переключение между окном логина и главным окном, темы.

Создаётся ровно один экземпляр на процесс. Принимает зависимости снаружи
(callable для аутентификации, фабрика главного окна, шина событий) —
это упрощает интеграционные тесты и держит модуль свободным от глобальных
импортов БД.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from app.core.config import get_settings
from app.core.events import AppBus
from app.db.session import new_session
from app.services.auth import AuthService
from app.theme import apply_theme, get_theme
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)


class AppController(QObject):
    """Управляет жизненным циклом окон и сменой темы."""

    def __init__(self, app: QApplication) -> None:
        """Привязать контроллер к запущенному ``QApplication``."""
        super().__init__()
        self._app = app
        self._bus = AppBus()
        self._theme_name = get_settings().app_theme
        self._login = LoginWindow(authenticate=self._authenticate)
        self._main: MainWindow | None = None
        self._main_session: Session | None = None

    def start(self) -> None:
        """Показать окно логина (точка входа GUI)."""
        apply_theme(self._app, get_theme(self._theme_name))
        self._login.logged_in.connect(self._on_logged_in)
        self._login.show()

    # ---- slots ----
    @Slot(object)
    def _on_logged_in(self, ctx: AuthContext) -> None:
        _log.info("Открываем главное окно для user_id=%s", ctx.user_id)
        self._main_session = new_session()
        self._main = MainWindow(ctx, self._main_session)
        self._main.set_theme_label(self._theme_name)
        self._main.logout_requested.connect(self._on_logout)
        self._main.theme_toggle_requested.connect(self._on_theme_toggle)
        self._main.show()
        self._login.hide()
        self._bus.emit_logged_in(ctx)

    @Slot()
    def _on_logout(self) -> None:
        if self._main is not None:
            self._main.close()
            self._main = None
        if self._main_session is not None:
            self._main_session.close()
            self._main_session = None
        self._bus.user_logged_out.emit()
        self._login.reset()
        self._login.show()

    @Slot()
    def _on_theme_toggle(self) -> None:
        self._theme_name = "dark" if self._theme_name == "light" else "light"
        apply_theme(self._app, get_theme(self._theme_name))
        if self._main is not None:
            self._main.set_theme_label(self._theme_name)
        self._bus.theme_changed.emit(self._theme_name)

    # ---- private ----
    def _authenticate(self, login: str, password: str) -> AuthContext:
        """Открыть свою сессию, выполнить login, закоммитить аудит (даже при ошибке)."""
        session = new_session()
        try:
            return AuthService(session).authenticate(login, password)
        finally:
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
