"""Тесты ``SqlConsoleService``: режимы, pending-транзакции, ошибки."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import create_engine, text

from app.models.base import Base
from app.services.sql_console import SqlConsoleService, SqlExecutionError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from sqlalchemy.engine import Engine


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    # Файл, а не :memory: — иначе разные коннекты видят разные БД и тесты
    # «есть ли изменения снаружи pending-транзакции» становятся бессмысленными.
    db_path = tmp_path / "test.sqlite"
    eng = create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(eng)
    with eng.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
                "VALUES ('I', 'Первая', 10, 1, 1), ('II', 'Вторая', 30, 3, 2)"
            )
        )
    yield eng
    eng.dispose()


@pytest.fixture
def service(engine: Engine) -> Iterator[SqlConsoleService]:
    # В тестах RO и RW — один и тот же engine; защита от записи в read-only режиме
    # реализуется отдельно на уровне postgres-роли (миграция 0004).
    svc = SqlConsoleService(rw_engine=engine, ro_engine=engine)
    yield svc
    svc.close()


class TestExecuteSelect:
    def test_select_returns_rows(self, service: SqlConsoleService) -> None:
        result = service.execute("SELECT code, name FROM difficulty ORDER BY code", readonly=True)
        assert result.returns_rows is True
        assert result.columns == ["code", "name"]
        assert result.rowcount == 2
        assert result.rows[0] == ("I", "Первая")
        assert result.needs_commit is False

    def test_empty_sql_raises(self, service: SqlConsoleService) -> None:
        with pytest.raises(SqlExecutionError, match="Пустой"):
            service.execute("", readonly=True)

    def test_syntax_error_raises(self, service: SqlConsoleService) -> None:
        with pytest.raises(SqlExecutionError):
            service.execute("NOT A VALID SQL STATEMENT", readonly=True)


class TestFullModeTransaction:
    def test_insert_in_full_mode_keeps_transaction_open(
        self, service: SqlConsoleService, engine: Engine
    ) -> None:
        result = service.execute(
            "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
            "VALUES ('III', 'Третья', 50, 5, 3)",
            readonly=False,
        )
        assert result.needs_commit is True
        assert service.has_pending is True

        # Внешнее соединение пока не видит вставку — она в открытой транзакции.
        with engine.connect() as fresh:
            count = fresh.execute(text("SELECT COUNT(*) FROM difficulty")).scalar_one()
        assert count == 2

    def test_commit_pending_persists(self, service: SqlConsoleService, engine: Engine) -> None:
        service.execute(
            "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
            "VALUES ('III', 'Третья', 50, 5, 3)",
            readonly=False,
        )
        service.commit_pending()
        assert service.has_pending is False

        with engine.connect() as fresh:
            count = fresh.execute(text("SELECT COUNT(*) FROM difficulty")).scalar_one()
        assert count == 3

    def test_rollback_pending_discards(self, service: SqlConsoleService, engine: Engine) -> None:
        service.execute(
            "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
            "VALUES ('III', 'Третья', 50, 5, 3)",
            readonly=False,
        )
        service.rollback_pending()
        assert service.has_pending is False

        with engine.connect() as fresh:
            count = fresh.execute(text("SELECT COUNT(*) FROM difficulty")).scalar_one()
        assert count == 2

    def test_new_execute_discards_previous_pending(
        self, service: SqlConsoleService, engine: Engine
    ) -> None:
        service.execute(
            "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
            "VALUES ('III', 'Третья', 50, 5, 3)",
            readonly=False,
        )
        # Второй запрос откатывает первый.
        service.execute("SELECT 1", readonly=False)
        service.rollback_pending()

        with engine.connect() as fresh:
            count = fresh.execute(text("SELECT COUNT(*) FROM difficulty")).scalar_one()
        assert count == 2  # вставка из первого execute не сохранилась


class TestReadOnlyMode:
    def test_read_only_select_does_not_leave_pending(self, service: SqlConsoleService) -> None:
        service.execute("SELECT * FROM difficulty", readonly=True)
        assert service.has_pending is False

    def test_read_only_insert_does_not_persist(
        self, service: SqlConsoleService, engine: Engine
    ) -> None:
        # SQLite в read-only test setup всё равно выполнит, но мы откатываем
        # сразу — изменений снаружи не должно быть видно. В production
        # это страхуется правами postgres-роли (миграция 0004).
        with suppress(SqlExecutionError):
            service.execute(
                "INSERT INTO difficulty (code, name, min_length_km, min_days, sort_order) "
                "VALUES ('III', 'Третья', 50, 5, 3)",
                readonly=True,
            )
        with engine.connect() as fresh:
            count = fresh.execute(text("SELECT COUNT(*) FROM difficulty")).scalar_one()
        assert count == 2
        assert service.has_pending is False
