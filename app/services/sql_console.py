"""Сервис исполнения произвольного SQL для GUI-консоли.

Поведение транзакций (см. спецификацию §5.4):

- **Read-only режим.** Подключение через переданный ``ro_engine``
  (в production — postgres-роль с ``SELECT``-only). Транзакция всегда
  откатывается после получения результата; ничего нельзя записать.
- **Full режим.** Подключение через ``rw_engine``. Транзакция остаётся
  **открытой** после выполнения — ждёт явного решения пользователя:
  ``commit_pending()`` или ``rollback_pending()``. Если пользователь
  запускает новый SQL — предыдущая транзакция автоматически откатывается.

Сервис управляет одним подключением за раз — на каждую вкладку SQL-консоли
заводится свой экземпляр.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import AppError

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection, Engine, Result

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SqlResult:
    """Результат одного запроса для отображения в UI."""

    columns: list[str]
    rows: list[tuple[Any, ...]]
    rowcount: int
    elapsed_ms: int
    returns_rows: bool
    needs_commit: bool
    notice: str = ""
    columns_list: list[str] = field(default_factory=list)  # alias для удобства

    @property
    def empty(self) -> bool:
        """``True``, если запрос ничего не вернул и не изменил (DDL и т.п.)."""
        return self.rowcount == 0 and not self.returns_rows


class SqlExecutionError(AppError):
    """Ошибка выполнения SQL-запроса (синтаксическая или из БД)."""


class SqlConsoleService:
    """Исполнитель SQL для UI-консоли. См. модульный docstring про режимы."""

    def __init__(self, rw_engine: Engine, ro_engine: Engine) -> None:
        """Привязать сервис к двум движкам: основному и read-only."""
        self._rw_engine = rw_engine
        self._ro_engine = ro_engine
        self._pending: Connection | None = None

    # ---- public api ----
    def execute(self, sql: str, *, readonly: bool) -> SqlResult:
        """Выполнить ``sql`` в нужном режиме и вернуть :class:`SqlResult`.

        Если перед вызовом была активна транзакция полного режима — она
        откатывается. В режиме read-only результат сразу зафиксирован
        (transaction rolled back). В full-режиме — соединение остаётся
        в pending-состоянии до ``commit_pending``/``rollback_pending``.
        """
        sql = sql.strip()
        if not sql:
            raise SqlExecutionError("Пустой SQL-запрос")

        self._discard_pending()
        engine = self._ro_engine if readonly else self._rw_engine
        conn = engine.connect()
        started = time.perf_counter()
        try:
            result: Result = conn.execute(text(sql))
        except SQLAlchemyError as exc:
            self._close_quietly(conn)
            _log.warning("SQL error (readonly=%s): %s", readonly, exc)
            raise SqlExecutionError(f"{exc.__class__.__name__}: {exc}") from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)

        if result.returns_rows:
            rows = [tuple(r) for r in result.fetchall()]
            columns = list(result.keys())
            rowcount = len(rows)
            returns_rows = True
        else:
            rows = []
            columns = []
            rc = result.rowcount
            rowcount = rc if rc is not None and rc >= 0 else 0
            returns_rows = False

        if readonly:
            conn.rollback()
            self._close_quietly(conn)
            return SqlResult(
                columns=columns,
                rows=rows,
                rowcount=rowcount,
                elapsed_ms=elapsed_ms,
                returns_rows=returns_rows,
                needs_commit=False,
                notice="Read-only: транзакция автоматически откачена.",
            )

        self._pending = conn
        return SqlResult(
            columns=columns,
            rows=rows,
            rowcount=rowcount,
            elapsed_ms=elapsed_ms,
            returns_rows=returns_rows,
            needs_commit=True,
            notice=(
                "Транзакция открыта — нажмите «Применить» для COMMIT или «Откатить» для ROLLBACK."
            ),
        )

    def commit_pending(self) -> None:
        """Зафиксировать активную транзакцию full-режима (если есть)."""
        if self._pending is None:
            return
        try:
            self._pending.commit()
        finally:
            self._close_quietly(self._pending)
            self._pending = None

    def rollback_pending(self) -> None:
        """Откатить активную транзакцию full-режима (если есть)."""
        if self._pending is None:
            return
        try:
            self._pending.rollback()
        finally:
            self._close_quietly(self._pending)
            self._pending = None

    @property
    def has_pending(self) -> bool:
        """Открыта ли сейчас транзакция, ждущая COMMIT/ROLLBACK."""
        return self._pending is not None

    def close(self) -> None:
        """Закрыть сервис (для жизненного цикла окна): откатить незакрытую транзакцию."""
        self.rollback_pending()

    # ---- private ----
    def _discard_pending(self) -> None:
        if self._pending is not None:
            try:
                self._pending.rollback()
            finally:
                self._close_quietly(self._pending)
                self._pending = None

    @staticmethod
    def _close_quietly(conn: Connection) -> None:
        try:
            conn.close()
        except SQLAlchemyError:
            _log.debug("Failed to close connection", exc_info=True)
