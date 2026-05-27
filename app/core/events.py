"""Глобальная шина приложения для кросс-экранных сигналов (см. спецификацию §5.6).

На шину кладутся **только** события, которые должны быть доступны более чем
одному экрану/виджету (вход пользователя, смена темы, инвалидация данных).
Локальные взаимодействия между соседями — обычные Qt-сигналы, не шина.

Экземпляр один на процесс — :func:`get_bus`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

if TYPE_CHECKING:
    from app.services.acl import AuthContext


class AppBus(QObject):
    """Кросс-экранная шина типизированных сигналов."""

    user_logged_in = Signal(object)  # payload: AuthContext
    user_logged_out = Signal()
    theme_changed = Signal(str)  # payload: имя темы
    data_invalidated = Signal(str)  # payload: имя сущности или "*" для «всё»

    def emit_logged_in(self, ctx: AuthContext) -> None:
        """Шорткат для типизированного эмита события входа."""
        self.user_logged_in.emit(ctx)

    def emit_data_invalidated(self, scope: str = "*") -> None:
        """Сообщить всем подписчикам, что данные `scope` могли измениться."""
        self.data_invalidated.emit(scope)


_bus: AppBus | None = None


def get_bus() -> AppBus:
    """Вернуть единственный на процесс экземпляр :class:`AppBus`."""
    global _bus  # noqa: PLW0603 — ленивый синглтон шины на процесс
    if _bus is None:
        _bus = AppBus()
    return _bus
