"""Универсальный диалог-форма для создания/редактирования сущности."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select

from app.core.errors import ValidationError
from app.ui.crud.descriptor import FieldKind, FormField

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.base import Base


class FormDialog(QDialog):
    """Диалог редактирования: строит inputs из :class:`FormField`-ов."""

    # ---- init ----
    def __init__(
        self,
        title: str,
        fields: list[FormField],
        session: Session,
        instance: Base | None = None,
        parent: QWidget | None = None,
    ) -> None:
        """Создать диалог. Если ``instance`` задан — поля предзаполняются из него."""
        super().__init__(parent)
        self._fields = fields
        self._session = session
        self._instance = instance
        self._inputs: dict[str, QWidget] = {}
        self._error_label: QLabel
        self.setWindowTitle(title)
        self.setMinimumWidth(480)
        self._build_ui()
        self._wire()
        if instance is not None:
            self._populate_from(instance)

    # ---- public api ----
    def values(self) -> dict[str, Any]:
        """Собрать значения полей; бросить :class:`ValidationError` при пустых обязательных."""
        result: dict[str, Any] = {}
        missing: list[str] = []
        for field in self._fields:
            value = self._read_input(field)
            if field.required and self._is_blank(value):
                missing.append(field.label)
                continue
            result[field.name] = value
        if missing:
            raise ValidationError("Заполните обязательные поля: " + ", ".join(missing))
        return result

    # ---- private ----
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setSpacing(8)

        for field in self._fields:
            widget = self._make_input(field)
            self._inputs[field.name] = widget
            label_text = field.label + (" *" if field.required else "")
            lbl = QLabel(label_text)
            lbl.setObjectName("FieldLabel")
            form.addRow(lbl, widget)

        outer.addLayout(form)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        outer.addWidget(self._error_label)

        outer.addStretch(1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setObjectName("SecondaryButton")

        wrap = QHBoxLayout()
        wrap.addStretch(1)
        wrap.addWidget(buttons)
        outer.addLayout(wrap)

        self._buttons = buttons

    def _wire(self) -> None:
        self._buttons.accepted.connect(self._on_accept)
        self._buttons.rejected.connect(self.reject)

    def _on_accept(self) -> None:
        try:
            self.values()  # запустить валидацию
        except ValidationError as exc:
            self._error_label.setText(str(exc))
            return
        self.accept()

    def _make_input(self, field: FormField) -> QWidget:
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
                for value, label in field.choices or []:
                    w.addItem(label, value)
                return w
            case FieldKind.RELATION:
                w = QComboBox()
                if not field.required:
                    w.addItem("—", None)
                for obj in self._load_relation(field):
                    label = self._format_relation(obj, field.relation_label_field)
                    w.addItem(label, obj)
                return w
            case _:
                raise ValueError(f"Неизвестный тип поля: {field.kind}")

    def _read_input(self, field: FormField) -> Any:
        widget = self._inputs[field.name]
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
                obj = widget.currentData()  # type: ignore[union-attr]
                if obj is None:
                    return None
                # Возвращаем сам объект — каллер решит, как записать в FK-поле.
                return obj
            case _:
                return None

    def _populate_from(self, instance: Base) -> None:
        for field in self._fields:
            widget = self._inputs[field.name]
            value = getattr(instance, field.name, None)
            if value is None and field.kind not in {FieldKind.BOOL, FieldKind.RELATION}:
                continue
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
                    # value — связанный ORM-объект; ищем совпадение по PK.
                    target_pk = self._pk_of(value) if value is not None else None
                    combo: QComboBox = widget  # type: ignore[assignment]
                    for i in range(combo.count()):
                        obj = combo.itemData(i)
                        item_pk = self._pk_of(obj) if obj is not None else None
                        if item_pk == target_pk:
                            combo.setCurrentIndex(i)
                            break

    def _load_relation(self, field: FormField) -> list[Base]:
        if field.relation_model is None:
            return []
        return list(self._session.execute(select(field.relation_model)).scalars())

    @staticmethod
    def _format_relation(obj: Base, label_field: str) -> str:
        value = getattr(obj, label_field, None)
        return str(value) if value is not None else f"<{type(obj).__name__} #{obj}>"

    @staticmethod
    def _pk_of(obj: Base) -> Any:
        mapper = sa_inspect(type(obj))
        pk_cols = mapper.primary_key
        if len(pk_cols) != 1:
            return None
        return getattr(obj, pk_cols[0].name)

    @staticmethod
    def _is_blank(value: Any) -> bool:
        if value is None:
            return True
        return bool(isinstance(value, str) and not value.strip())
