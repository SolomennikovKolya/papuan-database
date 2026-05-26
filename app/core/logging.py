"""Настройка корневого логгера приложения.

Используется стандартный модуль ``logging``. Конфигурация делается один раз
при старте процесса вызовом :func:`setup_logging`. Все модули получают свой
логгер обычным ``logging.getLogger(__name__)``.

Логи пишутся одновременно:
- в stderr (для разработки);
- в файл ``logs/app.log`` с ротацией (5 МБ × 5 файлов).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_HANDLER_MARK = "app.core.logging"


def setup_logging(level: str = "INFO", log_dir: Path | str = "logs") -> None:
    """Сконфигурировать корневой логгер.

    Идемпотентна: повторный вызов перенастраивает уровень, но не плодит
    дублирующиеся хендлеры (отличаем «свои» по полю ``name``).

    Args:
        level: уровень логирования (``DEBUG``/``INFO``/``WARNING``/``ERROR``).
        log_dir: каталог для файла логов. Будет создан, если не существует.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())

    if any(getattr(h, "name", None) == _HANDLER_MARK for h in root.handlers):
        return

    formatter = logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.set_name(_HANDLER_MARK)
    root.addHandler(stream_handler)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.set_name(_HANDLER_MARK)
    root.addHandler(file_handler)

    # SQLAlchemy очень шумит на DEBUG — оставим её на WARNING по умолчанию.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
