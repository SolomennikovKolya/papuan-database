"""QSS-шаблон и применение темы к ``QApplication``.

QSS собирается **только** из токенов :class:`Theme`. Никаких инлайновых
``setStyleSheet`` в коде виджетов: всё, что нужно стилизовать, помечается
``setObjectName(...)`` и описывается здесь.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

    from app.theme.tokens import Theme


_QSS_TEMPLATE = """
* {{
    font-family: {font_family};
    font-size: {font_size_md}px;
    color: {fg_primary};
}}

QMainWindow, QDialog, QWidget#RootContent {{
    background-color: {bg_app};
}}

/* ---- Sidebar ---- */
QWidget#Sidebar {{
    background-color: {bg_surface_alt};
    border-right: 1px solid {border_subtle};
}}
QLabel#SidebarBrand {{
    color: {fg_primary};
    font-size: {font_size_lg}px;
    font-weight: 700;
    padding: {spacing_lg}px {spacing_lg}px {spacing_md}px {spacing_lg}px;
}}
QLabel#SidebarFooter {{
    color: {fg_muted};
    font-size: {font_size_sm}px;
    padding: {spacing_sm}px {spacing_lg}px;
}}

QPushButton#NavItem {{
    background: transparent;
    text-align: left;
    padding: {spacing_md}px {spacing_lg}px;
    border: none;
    border-left: 3px solid transparent;
    color: {fg_secondary};
    font-size: {font_size_md}px;
}}
QPushButton#NavItem:hover {{
    background-color: {bg_hover};
    color: {fg_primary};
}}
QPushButton#NavItem:checked {{
    background-color: {bg_pressed};
    color: {fg_primary};
    border-left: 3px solid {accent};
    font-weight: 600;
}}

/* ---- Buttons ---- */
QPushButton#PrimaryButton {{
    background-color: {accent};
    color: {fg_on_accent};
    border: none;
    border-radius: {radius_md}px;
    padding: {spacing_sm}px {spacing_lg}px;
    font-weight: 600;
    min-height: 28px;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {accent_hover};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: {accent_pressed};
}}
QPushButton#PrimaryButton:disabled {{
    background-color: {bg_pressed};
    color: {fg_muted};
}}

QPushButton#SecondaryButton {{
    background-color: transparent;
    color: {fg_primary};
    border: 1px solid {border_strong};
    border-radius: {radius_md}px;
    padding: {spacing_sm}px {spacing_lg}px;
    min-height: 28px;
}}
QPushButton#SecondaryButton:hover {{
    background-color: {bg_hover};
    border-color: {accent};
}}
QPushButton#SecondaryButton:pressed {{
    background-color: {bg_pressed};
}}

QPushButton#GhostButton {{
    background-color: transparent;
    color: {fg_secondary};
    border: none;
    padding: {spacing_xs}px {spacing_sm}px;
    border-radius: {radius_sm}px;
}}
QPushButton#GhostButton:hover {{
    background-color: {bg_hover};
    color: {fg_primary};
}}

/* ---- Inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox, QDateEdit, QDateTimeEdit {{
    background-color: {bg_input};
    color: {fg_primary};
    border: 1px solid {border_subtle};
    border-radius: {radius_md}px;
    padding: {spacing_sm}px {spacing_md}px;
    selection-background-color: {accent};
    selection-color: {fg_on_accent};
    min-height: 22px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    border: 1px solid {border_focus};
}}
QLineEdit:disabled, QComboBox:disabled {{
    background-color: {bg_surface_alt};
    color: {fg_muted};
}}

/* ---- Cards / surfaces ---- */
QFrame#Card {{
    background-color: {bg_surface};
    border: 1px solid {border_subtle};
    border-radius: {radius_lg}px;
}}

QLabel#FieldLabel {{
    color: {fg_secondary};
    font-size: {font_size_sm}px;
    font-weight: 500;
}}
QLabel#H1 {{
    font-size: {font_size_xl}px;
    font-weight: 700;
    color: {fg_primary};
}}
QLabel#H2 {{
    font-size: {font_size_lg}px;
    font-weight: 600;
    color: {fg_primary};
}}
QLabel#Muted {{
    color: {fg_muted};
    font-size: {font_size_sm}px;
}}
QLabel#ErrorLabel {{
    color: {state_danger};
    font-size: {font_size_sm}px;
}}

QStatusBar {{
    background-color: {bg_surface_alt};
    color: {fg_muted};
    border-top: 1px solid {border_subtle};
}}

/* ---- Scrollbars ---- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {border_strong};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {fg_muted};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: {border_strong};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""


def render_qss(theme: Theme) -> str:
    """Подставить токены темы в QSS-шаблон и вернуть готовую строку."""
    return _QSS_TEMPLATE.format(**asdict(theme))


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Применить тему к ``QApplication`` (заменяет глобальный stylesheet)."""
    app.setStyleSheet(render_qss(theme))
    app.setProperty("themeName", theme.name)
