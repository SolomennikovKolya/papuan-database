"""Декларативное описание сущности для дженерик-CRUD UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.models.base import Base


class FieldKind(Enum):
    """Тип поля в форме редактирования — определяет, какой Qt-виджет рисовать."""

    TEXT = "text"
    TEXTAREA = "textarea"
    INT = "int"
    DECIMAL = "decimal"
    BOOL = "bool"
    DATE = "date"
    DATETIME = "datetime"
    CHOICE = "choice"
    RELATION = "relation"


@dataclass(frozen=True)
class Column:
    """Описание одной колонки таблицы.

    ``field`` — имя атрибута модели, либо «путь через точку» для связанных
    объектов (``"section.name"``). ``formatter`` — необязательная функция,
    превращающая значение в строку (по умолчанию ``str(value)``).
    """

    field: str
    title: str
    width: int | None = None
    align: str = "left"
    formatter: Callable[[Any], str] | None = None


@dataclass(frozen=True)
class FormField:
    """Описание одного поля в форме редактирования."""

    name: str
    label: str
    kind: FieldKind
    required: bool = True
    choices: list[tuple[Any, str]] | None = None
    relation_model: type[Base] | None = None
    relation_label_field: str = "name"
    min_value: int | float | None = None
    max_value: int | float | None = None
    default: Any = None
    placeholder: str = ""


@dataclass(frozen=True)
class EntityDescriptor[ModelT: Base]:
    """Полное описание сущности: модель, колонки таблицы, поля формы, права."""

    model: type[ModelT]
    title: str
    title_singular: str
    columns: list[Column]
    form_fields: list[FormField]
    perm_prefix: str
    default_sort: str = "id"
    search_field: str | None = None
    page_size: int = 25
    extra_filters: list[Callable[[str], Any]] = field(default_factory=list)
