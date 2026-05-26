"""CLI-утилиты для администрирования и диагностики (``python -m app.cli ...``).

На этапе 1 поддерживается единственная команда — ``check-db``: проверяет, что
приложение видит БД с теми настройками, что лежат в ``.env``. По мере роста
проекта сюда добавятся команды для миграций, посева данных и т.п.
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.engine import dispose_all, get_engine, get_readonly_engine

_log = logging.getLogger(__name__)


def _cmd_check_db(args: argparse.Namespace) -> int:
    """Проверить подключение к БД (основное и, опционально, read-only)."""
    settings = get_settings()
    print(f"DB URL: {settings.db_url.render_as_string(hide_password=True)}")

    exit_code = 0
    targets: list[tuple[str, object]] = [("main", get_engine())]
    if args.readonly:
        targets.append(("readonly", get_readonly_engine()))

    for label, engine in targets:
        try:
            with engine.connect() as conn:  # type: ignore[union-attr]
                version = conn.execute(text("SELECT version()")).scalar_one()
            print(f"  [{label}] OK — {version}")
        except SQLAlchemyError as exc:
            print(f"  [{label}] FAIL — {exc.__class__.__name__}: {exc}", file=sys.stderr)
            _log.exception("Connection check failed for %s", label)
            exit_code = 1
    return exit_code


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Утилиты администрирования ИС туристического клуба.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check-db", help="Проверить подключение к БД")
    p_check.add_argument(
        "--readonly",
        action="store_true",
        help="Дополнительно проверить read-only пользователя",
    )
    p_check.set_defaults(func=_cmd_check_db)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI: разобрать аргументы, выполнить подкоманду, вернуть код."""
    settings = get_settings()
    setup_logging(level=settings.app_log_level)

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    finally:
        dispose_all()


if __name__ == "__main__":
    raise SystemExit(main())
