"""Общие виджеты с предустановленными ``objectName`` для темизации.

В коде виджетов **не** должно быть инлайновых ``setStyleSheet`` —
вид определяется только QSS-шаблоном :mod:`app.theme.qss`, который
матчит элементы по ``objectName``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFrame, QPushButton

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class PrimaryButton(QPushButton):
    """Главная кнопка действия (сабмит формы, подтверждение)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        """Создать кнопку с текстом и навесить ``objectName='PrimaryButton'``."""
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")
        self.setCursor(self.cursor().shape())


class SecondaryButton(QPushButton):
    """Вторичная кнопка (отмена, дополнительные действия)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        """Создать кнопку с текстом и ``objectName='SecondaryButton'``."""
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")


class GhostButton(QPushButton):
    """Прозрачная кнопка для второстепенных ссылок-действий (logout, smaller links)."""

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        """Создать кнопку с текстом и ``objectName='GhostButton'``."""
        super().__init__(text, parent)
        self.setObjectName("GhostButton")


class Card(QFrame):
    """Контейнер-«карточка» с фоном и скруглением (для группировки секций экрана)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Создать пустую карточку без layout — каллер сам задаёт layout и содержимое."""
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFrameShape(QFrame.Shape.NoFrame)
