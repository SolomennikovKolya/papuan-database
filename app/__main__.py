"""Точка входа GUI: ``python -m app``.

На этапе 1 здесь читается конфигурация, поднимается логирование и показывается
временное «Hello, Qt» окно. По мере развития проекта тут появятся: DI-контейнер,
проверка подключения к БД, окно логина и главное окно.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.engine import dispose_all

_log = logging.getLogger(__name__)


class _HelloWindow(QMainWindow):
    """Временное главное окно для проверки запуска Qt."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Tourist Club — Hello, Qt")
        self.resize(480, 240)
        label = QLabel("Hello, Qt!\n\nЭтап 1 пройден.", self)
        label.setObjectName("HelloLabel")
        self.setCentralWidget(label)


def main() -> int:
    """Запустить приложение и вернуть код завершения процесса."""
    settings = get_settings()
    setup_logging(level=settings.app_log_level)
    _log.info("Запуск приложения, тема=%s", settings.app_theme)

    app = QApplication(sys.argv)
    window = _HelloWindow()
    window.show()
    try:
        return app.exec()
    finally:
        dispose_all()


if __name__ == "__main__":
    raise SystemExit(main())
