"""Главное окно: sidebar навигации + контентный стек.

Реальные страницы для разделов «Справочники», «Тренировки», «Походы»
строятся из дескрипторов в :mod:`app.ui.descriptors`. Разделы «Запросы»,
«SQL-консоль», «Администрирование» и «Сервисный режим» остаются заглушками
до соответствующих этапов плана (см. ``docs/plan.md``).
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

from app.ui.descriptors import (
    REFERENCE_DESCRIPTORS,
    TRAINING_DESCRIPTORS,
    TRIP_DESCRIPTORS,
)
from app.ui.pages import EntityListPage, make_placeholder
from app.ui.queries.page import QueriesPage
from app.ui.widgets import GhostButton

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext


@dataclass(frozen=True)
class _Section:
    """Описание раздела sidebar-а: ключ, заголовок, право, фабрика страницы."""

    key: str
    title: str
    required_permission: str | None
    page_factory: Callable[[Session, AuthContext], QWidget]


def _references_factory(session: Session, ctx: AuthContext) -> QWidget:
    return EntityListPage(REFERENCE_DESCRIPTORS, session, ctx)


def _training_factory(session: Session, ctx: AuthContext) -> QWidget:
    return EntityListPage(TRAINING_DESCRIPTORS, session, ctx)


def _trips_factory(session: Session, ctx: AuthContext) -> QWidget:
    return EntityListPage(TRIP_DESCRIPTORS, session, ctx)


def _queries_factory(session: Session, ctx: AuthContext) -> QWidget:
    return QueriesPage(session, ctx)


def _sql_stub(_session: Session, _ctx: AuthContext) -> QWidget:
    return make_placeholder("SQL-консоль", "SQL-консоль (read-only + RW) будет на этапе 8.")


def _admin_stub(_session: Session, _ctx: AuthContext) -> QWidget:
    return make_placeholder(
        "Администрирование",
        "Управление пользователями, ролями и журналом входов появится на этапе 9.",
    )


def _service_stub(_session: Session, _ctx: AuthContext) -> QWidget:
    return make_placeholder(
        "Сервисный режим",
        "Очистка БД, посев демо-данных и экспорт дампа — этап 10.",
    )


_SECTIONS: tuple[_Section, ...] = (
    _Section("references", "Справочники", "tourist.read", _references_factory),
    _Section("training", "Тренировки", "training_session.read", _training_factory),
    _Section("trips", "Походы", "trip.read", _trips_factory),
    _Section("queries", "Запросы по варианту", None, _queries_factory),
    _Section("sql", "SQL-консоль", "sql.execute", _sql_stub),
    _Section("admin", "Администрирование", "admin.users", _admin_stub),
    _Section("service", "Сервисный режим", "service.testdata", _service_stub),
)


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    # ---- signals ----
    logout_requested = Signal()
    theme_toggle_requested = Signal()

    # ---- init ----
    def __init__(self, ctx: AuthContext, session: Session) -> None:
        """Построить окно для уже вошедшего пользователя и заданной сессии."""
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
        """Программно открыть раздел по его ключу (см. ``_SECTIONS``)."""
        btn = self._nav_buttons.get(key)
        if btn is not None:
            btn.click()

    def set_theme_label(self, theme_name: str) -> None:
        """Обновить подпись переключателя темы (``light``/``dark``)."""
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
