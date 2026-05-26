"""Дженерик CRUD-инфраструктура для PySide6.

`EntityDescriptor` декларативно описывает сущность; `CrudView` строит по
описанию рабочий экран с таблицей, поиском, пагинацией и диалогом формы.
"""

from __future__ import annotations

from app.ui.crud.crud_view import CrudView
from app.ui.crud.descriptor import (
    Column,
    EntityDescriptor,
    FieldKind,
    FormField,
)

__all__ = [
    "Column",
    "CrudView",
    "EntityDescriptor",
    "FieldKind",
    "FormField",
]
