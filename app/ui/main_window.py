"""Главное окно: sidebar навигации + контентный стек.

4 раздела:
* «Данные» — все CRUD-справочники, тренировки и походы в одном экране,
  разбитые на смысловые группы (см. ``DATA_GROUPS`` в ``descriptors.py``).
* «Консоль» — готовые запросы по варианту + произвольный SQL.
* «Администрирование» — пользователи, роли, журнал входов.
* «Сервисный режим» — очистка БД, посев демо-данных, экспорт дампа.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.admin import AdminPage
from app.ui.console_page import ConsolePage
from app.ui.descriptors import DATA_GROUPS
from app.ui.pages import DataPage
from app.ui.service_panel import ServicePanel
from app.ui.widgets import GhostButton

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext


@dataclass(frozen=True)
class _Section:
    """Описание раздела sidebar-а."""

    key: str
    title: str
    required_permission: str | None
    page_factory: Callable[[Session, AuthContext], QWidget]


def _data_factory(session: Session, ctx: AuthContext) -> QWidget:
    return DataPage(DATA_GROUPS, session, ctx)


def _console_factory(session: Session, ctx: AuthContext) -> QWidget:
    return ConsolePage(session, ctx)


def _admin_factory(session: Session, ctx: AuthContext) -> QWidget:
    return AdminPage(session, ctx)


def _service_factory(session: Session, ctx: AuthContext) -> QWidget:
    return ServicePanel(session, ctx)


_SECTIONS: tuple[_Section, ...] = (
    _Section("data", "Данные", None, _data_factory),
    _Section("console", "Консоль", None, _console_factory),
    _Section("admin", "Администрирование", "admin.users", _admin_factory),
    _Section("service", "Сервисный режим", "service.testdata", _service_factory),
)


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    # ---- signals ----
    logout_requested = Signal()
    theme_toggle_requested = Signal()

    # ---- init ----
    def __init__(self, ctx: AuthContext, session: Session) -> None:
        """Построить окно для вошедшего пользователя и заданной сессии."""
        super().__init__()
        self._ctx = ctx
        self._session = session
        self._nav_group: QButtonGroup
        self._nav_buttons: dict[str, QPushButton] = {}
        self._stack: QStackedWidget
        self._theme_btn: GhostButton
        self.setWindowTitle(f"Tourist Club — {ctx.login}")
        self.resize(1280, 800)
        self._build_ui()
        self._wire()

    # ---- public api ----
    def set_active_section(self, key: str) -> None:
        """Программно открыть раздел по его ключу."""
        btn = self._nav_buttons.get(key)
        if btn is not None:
            btn.click()

    def set_theme_label(self, theme_name: str) -> None:
        """Обновить подпись переключателя темы."""
        opposite = "тёмная" if theme_name == "light" else "светлая"
        self._theme_btn.setText(f"Тема: {opposite}")

    # ---- slots ----
    @Slot(int)
    def _on_nav_clicked(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

    # ---- private ----
    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("RootContent")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())
        root.addWidget(self._build_content_stack(), 1)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar(self))
        self._refresh_status()

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        brand = QLabel("Tourist Club")
        brand.setObjectName("SidebarBrand")
        layout.addWidget(brand)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)

        index = 0
        for section in _SECTIONS:
            if not self._can_see(section):
                continue
            btn = QPushButton(section.title)
            btn.setObjectName("NavItem")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._nav_group.addButton(btn, index)
            self._nav_buttons[section.key] = btn
            layout.addWidget(btn)
            index += 1

        layout.addStretch(1)
        layout.addWidget(self._make_separator())

        user_label = QLabel(self._ctx.login)
        user_label.setObjectName("SidebarFooter")
        layout.addWidget(user_label)

        self._theme_btn = GhostButton("Тема: тёмная")
        self._theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._theme_btn)

        logout_btn = GhostButton("Выйти")
        logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        logout_btn.clicked.connect(self.logout_requested)
        layout.addWidget(logout_btn)

        return sidebar

    def _build_content_stack(self) -> QWidget:
        self._stack = QStackedWidget()
        for section in _SECTIONS:
            if not self._can_see(section):
                continue
            page = section.page_factory(self._session, self._ctx)
            self._stack.addWidget(page)
        return self._stack

    def _make_separator(self) -> QWidget:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setFixedHeight(1)
        return line

    def _can_see(self, section: _Section) -> bool:
        if section.required_permission is None:
            return True
        return self._ctx.has(section.required_permission)

    def _wire(self) -> None:
        self._nav_group.idClicked.connect(self._on_nav_clicked)
        self._theme_btn.clicked.connect(self.theme_toggle_requested)
        first = next(iter(self._nav_buttons.values()), None)
        if first is not None:
            first.setChecked(True)
            self._stack.setCurrentIndex(0)

    def _refresh_status(self) -> None:
        role_marker = " (superadmin)" if self._ctx.is_superadmin else ""
        self.statusBar().showMessage(
            f"Вошёл как {self._ctx.login}{role_marker} · прав: {len(self._ctx.permissions)}"
        )
