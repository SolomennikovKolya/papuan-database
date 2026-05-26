"""Глобальная шина приложения для кросс-экранных сигналов (см. спецификацию §5.6).

На шину кладутся **только** события, которые должны быть доступны более чем
одному экрану/виджету (вход пользователя, смена темы, инвалидация данных).
Локальные взаимодействия между соседями — обычные Qt-сигналы, не шина.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from app.services.acl import AuthContext


class AppBus(QObject):
    """Кросс-экранная шина типизированных сигналов."""

    # Аутентификация
    user_logged_in = Signal(object)  # payload: AuthContext
    user_logged_out = Signal()

    # Темизация
    theme_changed = Signal(str)  # payload: имя темы

    # Уведомление: данные сущности изменились и UI-таблицы должны перечитаться
    data_invalidated = Signal(str)  # payload: имя сущности (e.g. "tourist")

    def emit_logged_in(self, ctx: AuthContext) -> None:
        """Шорткат для типизированного эмита события входа."""
        self.user_logged_in.emit(ctx)
