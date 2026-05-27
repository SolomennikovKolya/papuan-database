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
QPushButton#PrimaryButton, QPushButton#SecondaryButton {{
    border-radius: {radius_md}px;
    padding: 0 {spacing_lg}px;
    min-height: 32px;
    max-height: 32px;
    font-weight: 500;
}}
QPushButton#PrimaryButton {{
    background-color: {accent};
    color: {fg_on_accent};
    border: 1px solid {accent};
}}
QPushButton#PrimaryButton:hover {{
    background-color: {accent_hover};
    border-color: {accent_hover};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: {accent_pressed};
    border-color: {accent_pressed};
}}
QPushButton#PrimaryButton:disabled {{
    background-color: {bg_disabled};
    color: {fg_disabled};
    border-color: {bg_disabled};
}}

QPushButton#SecondaryButton {{
    background-color: {bg_surface};
    color: {fg_primary};
    border: 1px solid {border_strong};
}}
QPushButton#SecondaryButton:hover {{
    background-color: {bg_hover};
    border-color: {accent};
    color: {fg_primary};
}}
QPushButton#SecondaryButton:pressed {{
    background-color: {bg_pressed};
}}
QPushButton#SecondaryButton:disabled {{
    background-color: {bg_surface_alt};
    color: {fg_disabled};
    border-color: {border_subtle};
}}

QPushButton#GhostButton {{
    background-color: transparent;
    color: {fg_secondary};
    border: none;
    padding: {spacing_sm}px {spacing_lg}px;
    text-align: left;
    border-radius: {radius_sm}px;
}}
QPushButton#GhostButton:hover {{
    background-color: {bg_hover};
    color: {fg_primary};
}}
QPushButton#GhostButton:disabled {{
    color: {fg_disabled};
}}

/* ---- Inputs ---- */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {{
    background-color: {bg_input};
    color: {fg_primary};
    border: 1px solid {border_subtle};
    border-radius: {radius_md}px;
    padding: 0 {spacing_md}px;
    selection-background-color: {accent};
    selection-color: {fg_on_accent};
    min-height: 32px;
    max-height: 32px;
}}
QPlainTextEdit, QTextEdit {{
    padding: {spacing_sm}px {spacing_md}px;
    min-height: 80px;
    max-height: none;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QDateTimeEdit:focus {{
    border-color: {border_focus};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QDateEdit:disabled {{
    background-color: {bg_surface_alt};
    color: {fg_disabled};
}}

/* ---- Combobox ---- */
QComboBox {{
    background-color: {bg_input};
    color: {fg_primary};
    border: 1px solid {border_subtle};
    border-radius: {radius_md}px;
    padding-left: {spacing_md}px;
    padding-right: 28px;
    min-height: 32px;
    max-height: 32px;
}}
QComboBox:focus {{
    border-color: {border_focus};
}}
QComboBox:disabled {{
    background-color: {bg_surface_alt};
    color: {fg_disabled};
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: none;
    width: 0;
    height: 0;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {fg_secondary};
    margin-right: 8px;
}}
QComboBox::down-arrow:on {{
    border-top: none;
    border-bottom: 6px solid {accent};
}}
QComboBox QAbstractItemView {{
    background-color: {bg_surface};
    color: {fg_primary};
    border: 1px solid {border_subtle};
    selection-background-color: {accent};
    selection-color: {fg_on_accent};
    outline: 0;
    padding: 4px;
}}

QCheckBox {{
    spacing: 8px;
    color: {fg_primary};
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {border_strong};
    border-radius: 3px;
    background-color: {bg_input};
}}
QCheckBox::indicator:hover {{
    border-color: {accent};
}}
QCheckBox::indicator:checked {{
    background-color: {accent};
    border-color: {accent};
}}
QCheckBox::indicator:disabled {{
    background-color: {bg_surface_alt};
    border-color: {border_subtle};
}}

/* ---- Tables / Lists ---- */
QTableView, QListWidget, QTreeView {{
    background-color: {bg_surface};
    alternate-background-color: {bg_surface_alt};
    color: {fg_primary};
    border: 1px solid {border_subtle};
    border-radius: {radius_md}px;
    gridline-color: {border_subtle};
    selection-background-color: {accent};
    selection-color: {fg_on_accent};
    outline: 0;
}}
QTableView::item, QListWidget::item, QTreeView::item {{
    padding: 6px 4px;
    border: none;
}}
QTableView::item:selected, QListWidget::item:selected, QTreeView::item:selected {{
    background-color: {accent};
    color: {fg_on_accent};
}}
QHeaderView {{
    background-color: {bg_surface_alt};
    border: none;
}}
QHeaderView::section {{
    background-color: {bg_surface_alt};
    color: {fg_secondary};
    padding: 8px 6px;
    border: none;
    border-right: 1px solid {border_subtle};
    border-bottom: 1px solid {border_subtle};
    font-weight: 600;
}}
QTableCornerButton::section {{
    background-color: {bg_surface_alt};
    border: none;
    border-right: 1px solid {border_subtle};
    border-bottom: 1px solid {border_subtle};
}}

QListWidget#GroupedList::item:disabled {{
    background-color: transparent;
    color: {fg_muted};
    font-weight: 700;
    font-size: {font_size_sm}px;
    padding: {spacing_md}px {spacing_md}px {spacing_xs}px {spacing_md}px;
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

/* ---- Tabs ---- */
QTabWidget::pane {{
    border: 1px solid {border_subtle};
    border-radius: {radius_md}px;
    background-color: {bg_surface};
    top: -1px;
}}
QTabBar::tab {{
    background-color: transparent;
    color: {fg_secondary};
    padding: 8px 18px;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: {radius_md}px;
    border-top-right-radius: {radius_md}px;
    margin-right: 2px;
}}
QTabBar::tab:hover {{
    color: {fg_primary};
    background-color: {bg_hover};
}}
QTabBar::tab:selected {{
    background-color: {bg_surface};
    color: {fg_primary};
    border-color: {border_subtle};
    font-weight: 600;
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
