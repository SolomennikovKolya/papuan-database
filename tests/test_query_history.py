"""Тесты ``QueryHistory``: добавление, дедуп, лимит, чтение/запись JSON."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.query_history import HistoryEntry, QueryHistory

if TYPE_CHECKING:
    from pathlib import Path


class TestQueryHistory:
    def test_empty_when_no_file(self, tmp_path: Path) -> None:
        h = QueryHistory(path=tmp_path / "missing.json")
        assert h.entries() == []

    def test_add_persists_and_reads_back(self, tmp_path: Path) -> None:
        path = tmp_path / "h.json"
        h = QueryHistory(path=path)
        h.add("SELECT 1", "readonly")
        h.add("SELECT 2", "full")

        reloaded = QueryHistory(path=path)
        entries = reloaded.entries()
        assert [e.sql for e in entries] == ["SELECT 2", "SELECT 1"]
        assert [e.mode for e in entries] == ["full", "readonly"]
        assert all(isinstance(e, HistoryEntry) for e in entries)

    def test_dedup_consecutive_same_sql(self, tmp_path: Path) -> None:
        h = QueryHistory(path=tmp_path / "h.json")
        h.add("SELECT 1", "readonly")
        h.add("SELECT 1", "readonly")
        h.add("SELECT 1", "readonly")
        assert len(h.entries()) == 1

    def test_max_entries_truncates(self, tmp_path: Path) -> None:
        h = QueryHistory(path=tmp_path / "h.json", max_entries=3)
        for i in range(5):
            h.add(f"SELECT {i}", "readonly")
        assert [e.sql for e in h.entries()] == ["SELECT 4", "SELECT 3", "SELECT 2"]

    def test_clear_removes_all(self, tmp_path: Path) -> None:
        h = QueryHistory(path=tmp_path / "h.json")
        h.add("SELECT 1", "readonly")
        h.clear()
        assert h.entries() == []

    def test_blank_sql_ignored(self, tmp_path: Path) -> None:
        h = QueryHistory(path=tmp_path / "h.json")
        h.add("   ", "readonly")
        h.add("", "readonly")
        assert h.entries() == []

    def test_corrupted_file_starts_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "h.json"
        path.write_text("not a json", encoding="utf-8")
        h = QueryHistory(path=path)
        assert h.entries() == []
