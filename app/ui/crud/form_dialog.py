"""Универсальный диалог-форма для создания/редактирования сущности."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import ValidationError
from app.ui.crud.form_builder import (
    is_blank,
    make_input,
    populate_input,
    read_input,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.base import Base
    from app.ui.crud.descriptor import FormField


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
            value = read_input(field, self._inputs[field.name])
            if field.required and is_blank(value):
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
            widget = make_input(field, self._session)
            self._inputs[field.name] = widget
            lbl = QLabel(field.label + (" *" if field.required else ""))
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

    def _populate_from(self, instance: Base) -> None:
        for field in self._fields:
            value = getattr(instance, field.name, None)
            populate_input(field, self._inputs[field.name], value)
