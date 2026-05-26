"""Smoke-тесты модуля запросов варианта 4.17."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.queries import RUNNERS
from app.ui.queries.descriptors import ALL_QUERIES

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class TestDescriptorsSanity:
    def test_has_all_thirteen(self) -> None:
        assert len(ALL_QUERIES) == 13

    def test_all_runners_present_and_callable(self) -> None:
        for d in ALL_QUERIES:
            assert callable(d.runner), f"{d.key}: runner не callable"

    def test_keys_match_runners_registry(self) -> None:
        descriptor_keys = {d.key for d in ALL_QUERIES}
        assert descriptor_keys == set(RUNNERS), (
            f"расхождение: дескрипторы={sorted(descriptor_keys)}, runners={sorted(RUNNERS)}"
        )

    def test_columns_non_empty(self) -> None:
        for d in ALL_QUERIES:
            assert d.result_columns, f"{d.key}: пустой список колонок результата"


class TestRunnersAgainstEmptyDb:
    """Каждый runner должен работать на пустой БД (вернуть []), без падений по SQL."""

    def test_each_runner_runs_clean(self, session: Session) -> None:
        for d in ALL_QUERIES:
            rows = d.runner(session, {})
            assert isinstance(rows, list), f"{d.key}: runner вернул не list"
