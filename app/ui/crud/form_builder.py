"""Построение Qt-input-ов по описанию :class:`FormField`.

Вынесено из ``form_dialog.py``, чтобы экраны запросов могли строить
фильтр-формы из тех же описаний.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select

from app.ui.crud.descriptor import FieldKind, FormField

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.base import Base


def make_input(field: FormField, session: Session) -> QWidget:
    """Создать виджет-input для поля по описанию ``FormField``."""
    match field.kind:
        case FieldKind.TEXT:
            w = QLineEdit()
            if field.placeholder:
                w.setPlaceholderText(field.placeholder)
            if field.max_value:
                w.setMaxLength(int(field.max_value))
            return w
        case FieldKind.TEXTAREA:
            w = QPlainTextEdit()
            w.setMinimumHeight(80)
            return w
        case FieldKind.INT:
            w = QSpinBox()
            w.setRange(
                int(field.min_value if field.min_value is not None else -(10**9)),
                int(field.max_value if field.max_value is not None else 10**9),
            )
            if field.default is not None:
                w.setValue(int(field.default))
            return w
        case FieldKind.DECIMAL:
            w = QDoubleSpinBox()
            w.setDecimals(2)
            w.setRange(
                float(field.min_value if field.min_value is not None else -1e12),
                float(field.max_value if field.max_value is not None else 1e12),
            )
            if field.default is not None:
                w.setValue(float(field.default))
            return w
        case FieldKind.BOOL:
            w = QCheckBox()
            if field.default:
                w.setChecked(bool(field.default))
            return w
        case FieldKind.DATE:
            w = QDateEdit()
            w.setCalendarPopup(True)
            w.setDate(QDate.currentDate())
            w.setDisplayFormat("yyyy-MM-dd")
            return w
        case FieldKind.CHOICE:
            w = QComboBox()
            if not field.required:
                w.addItem("—", None)
            for value, label in field.choices or []:
                w.addItem(label, value)
            return w
        case FieldKind.RELATION:
            w = QComboBox()
            if not field.required:
                w.addItem("—", None)
            for obj in _load_relation(field, session):
                w.addItem(_format_relation(obj, field.relation_label_field), obj)
            return w
        case _:
            raise ValueError(f"Неизвестный тип поля: {field.kind}")


def read_input(field: FormField, widget: QWidget) -> Any:
    """Считать текущее значение виджета и привести к нужному типу."""
    match field.kind:
        case FieldKind.TEXT:
            return widget.text().strip()  # type: ignore[union-attr]
        case FieldKind.TEXTAREA:
            return widget.toPlainText().strip()  # type: ignore[union-attr]
        case FieldKind.INT:
            return int(widget.value())  # type: ignore[union-attr]
        case FieldKind.DECIMAL:
            return Decimal(str(widget.value()))  # type: ignore[union-attr]
        case FieldKind.BOOL:
            return widget.isChecked()  # type: ignore[union-attr]
        case FieldKind.DATE:
            qd: QDate = widget.date()  # type: ignore[union-attr]
            return date(qd.year(), qd.month(), qd.day())
        case FieldKind.CHOICE:
            return widget.currentData()  # type: ignore[union-attr]
        case FieldKind.RELATION:
            return widget.currentData()  # type: ignore[union-attr]
        case _:
            return None


def populate_input(field: FormField, widget: QWidget, value: Any) -> None:
    """Установить значение виджета из существующего объекта (для редактирования)."""
    if value is None and field.kind not in {FieldKind.BOOL, FieldKind.RELATION}:
        return
    match field.kind:
        case FieldKind.TEXT:
            widget.setText(str(value or ""))  # type: ignore[union-attr]
        case FieldKind.TEXTAREA:
            widget.setPlainText(str(value or ""))  # type: ignore[union-attr]
        case FieldKind.INT:
            widget.setValue(int(value))  # type: ignore[union-attr]
        case FieldKind.DECIMAL:
            widget.setValue(float(value))  # type: ignore[union-attr]
        case FieldKind.BOOL:
            widget.setChecked(bool(value))  # type: ignore[union-attr]
        case FieldKind.DATE:
            widget.setDate(QDate(value.year, value.month, value.day))  # type: ignore[union-attr]
        case FieldKind.CHOICE:
            idx = widget.findData(value)  # type: ignore[union-attr]
            if idx >= 0:
                widget.setCurrentIndex(idx)  # type: ignore[union-attr]
        case FieldKind.RELATION:
            target_pk = pk_of(value) if value is not None else None
            combo: QComboBox = widget  # type: ignore[assignment]
            for i in range(combo.count()):
                obj = combo.itemData(i)
                item_pk = pk_of(obj) if obj is not None else None
                if item_pk == target_pk:
                    combo.setCurrentIndex(i)
                    break


def pk_of(obj: Base) -> Any:
    """Вернуть значение единственного PK ORM-объекта (или ``None`` для композитных)."""
    mapper = sa_inspect(type(obj))
    pk_cols = mapper.primary_key
    if len(pk_cols) != 1:
        return None
    return getattr(obj, pk_cols[0].name)


def is_blank(value: Any) -> bool:
    """Считать значение «пустым» (пропуск обязательного поля)."""
    if value is None:
        return True
    return bool(isinstance(value, str) and not value.strip())


def _load_relation(field: FormField, session: Session) -> list[Base]:
    if field.relation_model is None:
        return []
    return list(session.execute(select(field.relation_model)).scalars())


def _format_relation(obj: Base, label_field: str) -> str:
    value = getattr(obj, label_field, None)
    return str(value) if value is not None else f"<{type(obj).__name__}>"
