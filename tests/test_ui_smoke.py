"""UI smoke-тесты: рендер темы и базовая работа окна логина (pytest-qt)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from PySide6.QtWidgets import QApplication

from app.core.errors import AuthenticationError
from app.services.acl import AuthContext
from app.theme import apply_theme, available_themes, get_theme, render_qss
from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.ui.widgets import GhostButton

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot
    from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def _qt_app(qtbot: QtBot) -> None:
    """Гарантировать наличие QApplication для всех UI-тестов в файле."""
    _ = qtbot  # фикстура qtbot уже создаёт QApplication


class TestTheme:
    @pytest.mark.parametrize("name", ["light", "dark"])
    def test_render_qss_substitutes_all_tokens(self, name: str) -> None:
        theme = get_theme(name)
        qss = render_qss(theme)
        # Не должно остаться нераскрытых плейсхолдеров {token}.
        leftover = re.findall(r"\{[a-zA-Z_]+\}", qss)
        assert leftover == [], f"Несостоявшиеся подстановки: {leftover}"
        assert "background-color" in qss

    def test_unknown_theme_raises(self) -> None:
        with pytest.raises(ValueError, match="Неизвестная"):
            get_theme("hotpink")

    def test_available_themes_lists_both(self) -> None:
        assert {"light", "dark"}.issubset(available_themes())

    def test_apply_theme_sets_stylesheet(self, qtbot: QtBot) -> None:
        app = QApplication.instance()
        assert app is not None
        apply_theme(app, get_theme("dark"))
        assert app.styleSheet()
        assert app.property("themeName") == "dark"


def _superadmin_ctx(permissions: tuple[str, ...] = ()) -> AuthContext:
    return AuthContext(
        user_id=1,
        login="admin",
        is_superadmin=True,
        permissions=frozenset(permissions),
    )


class TestLoginWindow:
    def test_empty_fields_show_error(self, qtbot: QtBot) -> None:
        def fake_auth(_login: str, _pwd: str) -> AuthContext:
            raise AssertionError("authenticate не должен вызываться при пустых полях")

        window = LoginWindow(authenticate=fake_auth)
        qtbot.addWidget(window)
        window._submit_btn.click()
        assert "логин" in window._error_label.text().lower()

    def test_failed_auth_shows_error_keeps_window(self, qtbot: QtBot) -> None:
        def fake_auth(_login: str, _pwd: str) -> AuthContext:
            raise AuthenticationError("Неверный логин или пароль")

        window = LoginWindow(authenticate=fake_auth)
        qtbot.addWidget(window)
        window._login_edit.setText("admin")
        window._password_edit.setText("bad")
        window._submit_btn.click()
        assert "Неверный" in window._error_label.text()
        assert window.isVisible() is False or window.result() == 0

    def test_successful_auth_emits_signal(self, qtbot: QtBot) -> None:
        ctx = _superadmin_ctx()

        def fake_auth(login: str, password: str) -> AuthContext:
            assert login == "admin"
            assert password == "adminpass"
            return ctx

        window = LoginWindow(authenticate=fake_auth)
        qtbot.addWidget(window)
        window._login_edit.setText("admin")
        window._password_edit.setText("adminpass")
        with qtbot.waitSignal(window.logged_in, timeout=1000) as blocker:
            window._submit_btn.click()
        assert blocker.args == [ctx]


class TestMainWindow:
    def test_superadmin_sees_all_sections(self, qtbot: QtBot, session: Session) -> None:
        window = MainWindow(_superadmin_ctx(), session)
        qtbot.addWidget(window)
        # superadmin минует проверки прав — должен увидеть все 4 раздела.
        assert {"data", "console", "admin", "service"} <= set(window._nav_buttons)

    def test_user_without_permissions_hides_admin_section(
        self, qtbot: QtBot, session: Session
    ) -> None:
        ctx = AuthContext(user_id=2, login="weak", is_superadmin=False, permissions=frozenset())
        window = MainWindow(ctx, session)
        qtbot.addWidget(window)
        # Разделы без required_permission остаются (data, console); admin/service — нет.
        assert "admin" not in window._nav_buttons
        assert "service" not in window._nav_buttons
        assert "data" in window._nav_buttons
        assert "console" in window._nav_buttons

    def test_logout_signal_emitted_on_button(self, qtbot: QtBot, session: Session) -> None:
        window = MainWindow(_superadmin_ctx(), session)
        qtbot.addWidget(window)
        # Ищем GhostButton с текстом «Выйти» (CrudView тоже наплодит GhostButton-ов
        # для пагинатора, так что просто [-1] не подходит).
        logout_btn = next(b for b in window.findChildren(GhostButton) if b.text() == "Выйти")
        with qtbot.waitSignal(window.logout_requested, timeout=1000):
            logout_btn.click()
