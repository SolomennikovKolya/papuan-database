"""Тесты базового ``Repository``: CRUD, фильтры, сортировка, пагинация."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pytest

from app.core.errors import NotFound
from app.models import Difficulty
from app.repositories import Page, Repository, Sort

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@pytest.fixture
def repo(session: Session) -> Repository[Difficulty]:
    return Repository(session, Difficulty)


def _difficulty(code: str, sort_order: int, name: str | None = None) -> dict[str, Any]:
    return {
        "code": code,
        "name": name or f"Категория {code}",
        "min_length_km": Decimal("10"),
        "min_days": 1,
        "sort_order": sort_order,
    }


class TestCrud:
    def test_create_assigns_id(self, repo: Repository[Difficulty]) -> None:
        obj = repo.create(**_difficulty("I", 1))
        assert obj.id is not None
        assert obj.code == "I"

    def test_get_returns_persisted_object(self, repo: Repository[Difficulty]) -> None:
        obj = repo.create(**_difficulty("II", 2))
        assert repo.get(obj.id) is obj

    def test_get_missing_returns_none(self, repo: Repository[Difficulty]) -> None:
        assert repo.get(999) is None

    def test_get_or_raise_missing(self, repo: Repository[Difficulty]) -> None:
        with pytest.raises(NotFound):
            repo.get_or_raise(999)

    def test_update_changes_field(self, repo: Repository[Difficulty]) -> None:
        obj = repo.create(**_difficulty("III", 3))
        repo.update(obj, name="Третья")
        assert obj.name == "Третья"

    def test_update_unknown_field_raises(self, repo: Repository[Difficulty]) -> None:
        obj = repo.create(**_difficulty("IV", 4))
        with pytest.raises(AttributeError):
            repo.update(obj, no_such_field=1)

    def test_delete_removes_object(self, repo: Repository[Difficulty]) -> None:
        obj = repo.create(**_difficulty("V", 5))
        pk = obj.id
        repo.delete(obj)
        assert repo.get(pk) is None

    def test_delete_by_pk_missing_raises(self, repo: Repository[Difficulty]) -> None:
        with pytest.raises(NotFound):
            repo.delete_by_pk(999)


class TestList:
    @pytest.fixture
    def populated(self, repo: Repository[Difficulty]) -> Repository[Difficulty]:
        for i in range(5):
            repo.create(**_difficulty(f"D{i}", i))
        return repo

    def test_returns_page_with_total(self, populated: Repository[Difficulty]) -> None:
        page = populated.list()
        assert isinstance(page, Page)
        assert page.total == 5
        assert len(page.items) == 5

    def test_paginates_with_limit_and_offset(self, populated: Repository[Difficulty]) -> None:
        page = populated.list(limit=2, offset=2, order_by=[Sort("sort_order")])
        assert page.total == 5
        assert len(page.items) == 2
        assert page.items[0].sort_order == 2
        assert page.offset == 2
        assert page.limit == 2

    def test_where_filters_results(self, populated: Repository[Difficulty]) -> None:
        page = populated.list(where=[Difficulty.sort_order >= 3])
        assert page.total == 2
        assert {i.sort_order for i in page.items} == {3, 4}

    def test_order_by_descending(self, populated: Repository[Difficulty]) -> None:
        page = populated.list(order_by=[Sort("sort_order", descending=True)])
        assert [i.sort_order for i in page.items] == [4, 3, 2, 1, 0]

    def test_unknown_sort_field_raises(self, populated: Repository[Difficulty]) -> None:
        with pytest.raises(ValueError, match="отсутствует"):
            populated.list(order_by=[Sort("nope")])


class TestSortParse:
    def test_ascending_default(self) -> None:
        assert Sort.parse("name") == Sort("name", descending=False)

    def test_descending_with_minus_prefix(self) -> None:
        assert Sort.parse("-name") == Sort("name", descending=True)
