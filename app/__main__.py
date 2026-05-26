"""Точка входа GUI: ``python -m app``.

Поднимает конфиг и логирование, создаёт ``QApplication``, применяет тему,
запускает :class:`AppController` (окно логина → главное окно), штатно
освобождает пулы подключений на выходе.
"""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.engine import dispose_all
from app.ui.app_controller import AppController

_log = logging.getLogger(__name__)


def main() -> int:
    """Запустить приложение и вернуть код завершения процесса."""
    settings = get_settings()
    setup_logging(level=settings.app_log_level)
    _log.info("Запуск приложения, тема=%s", settings.app_theme)

    app = QApplication(sys.argv)
    controller = AppController(app)
    controller.start()
    try:
        return app.exec()
    finally:
        dispose_all()


if __name__ == "__main__":
    raise SystemExit(main())
