"""Дизайн-токены тем — единственный источник цветов/размеров для UI.

Все виджеты используют только эти токены (через QSS-шаблон в
:mod:`app.theme.qss`). Хардкодных цветов в коде виджетов быть не должно.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Полный набор семантических токенов одной темы."""

    name: str

    # --- backgrounds ---
    bg_app: str
    bg_surface: str
    bg_surface_alt: str
    bg_hover: str
    bg_pressed: str
    bg_input: str
    bg_disabled: str

    # --- text ---
    fg_primary: str
    fg_secondary: str
    fg_muted: str
    fg_disabled: str
    fg_on_accent: str

    # --- borders ---
    border_subtle: str
    border_strong: str
    border_focus: str

    # --- accent ---
    accent: str
    accent_hover: str
    accent_pressed: str

    # --- state ---
    state_danger: str
    state_warning: str
    state_success: str

    # --- geometry ---
    radius_sm: int = 4
    radius_md: int = 8
    radius_lg: int = 12

    spacing_xs: int = 4
    spacing_sm: int = 8
    spacing_md: int = 12
    spacing_lg: int = 16
    spacing_xl: int = 24

    font_size_sm: int = 12
    font_size_md: int = 14
    font_size_lg: int = 18
    font_size_xl: int = 22

    font_family: str = '"Segoe UI", "Inter", system-ui, sans-serif'


def light_theme() -> Theme:
    """Светлая тема (по умолчанию)."""
    return Theme(
        name="light",
        bg_app="#f4f6fa",
        bg_surface="#ffffff",
        bg_surface_alt="#eef1f6",
        bg_hover="#e3e8f0",
        bg_pressed="#d4dbe7",
        bg_input="#ffffff",
        bg_disabled="#eceff5",
        fg_primary="#1a1f2c",
        fg_secondary="#475266",
        fg_muted="#8794a8",
        fg_disabled="#b6bdc9",
        fg_on_accent="#ffffff",
        border_subtle="#e2e6ed",
        border_strong="#c4cbd6",
        border_focus="#3b82f6",
        accent="#2563eb",
        accent_hover="#1d4ed8",
        accent_pressed="#1e40af",
        state_danger="#dc2626",
        state_warning="#d97706",
        state_success="#16a34a",
    )


def dark_theme() -> Theme:
    """Тёмная тема."""
    return Theme(
        name="dark",
        bg_app="#0f1419",
        bg_surface="#1a212c",
        bg_surface_alt="#222a36",
        bg_hover="#2b3441",
        bg_pressed="#36414f",
        bg_input="#13181f",
        bg_disabled="#1d242e",
        fg_primary="#e6ebf2",
        fg_secondary="#9aa5b8",
        fg_muted="#5c6779",
        fg_disabled="#454e5c",
        fg_on_accent="#ffffff",
        border_subtle="#2a3240",
        border_strong="#3a4452",
        border_focus="#60a5fa",
        accent="#3b82f6",
        accent_hover="#60a5fa",
        accent_pressed="#2563eb",
        state_danger="#ef4444",
        state_warning="#f59e0b",
        state_success="#22c55e",
    )


_THEMES = {"light": light_theme, "dark": dark_theme}


def get_theme(name: str) -> Theme:
    """Вернуть тему по имени (``"light"`` или ``"dark"``)."""
    factory = _THEMES.get(name)
    if factory is None:
        raise ValueError(f"Неизвестная тема: {name!r}. Доступны: {sorted(_THEMES)}")
    return factory()


def available_themes() -> list[str]:
    """Список доступных имён тем."""
    return sorted(_THEMES)
