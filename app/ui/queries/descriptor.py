"""Декларативное описание хитрого запроса для дженерик ``QueryView``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from app.ui.crud.descriptor import FormField


@dataclass(frozen=True)
class ResultColumn:
    """Колонка таблицы результата запроса.

    В отличие от :class:`~app.ui.crud.descriptor.Column`, рассчитана на
    словарь-строку (``key`` — ключ в dict-результате), не на ORM-объект.
    """

    key: str
    title: str
    width: int | None = None
    align: str = "left"
    formatter: Any = None  # Callable[[Any], str] | None — обходим circular hints


@dataclass(frozen=True)
class QueryDescriptor:
    """Полное описание одного запроса варианта."""

    key: str
    title: str
    description: str
    params: list[FormField]
    result_columns: list[ResultColumn]
    runner: Callable[[Session, dict[str, Any]], list[dict[str, Any]]]
    perm: str = "tourist.read"
    extra: dict[str, Any] = field(default_factory=dict)
