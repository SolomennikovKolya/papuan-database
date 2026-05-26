"""Диалоги админ-панели: создание пользователя, смена пароля, роль, назначение ролей."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.errors import ValidationError
from app.ui.widgets import PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from app.models import Role


_MIN_PASSWORD_LEN = 4


class _BaseDialog(QDialog):
    """Общий каркас для админ-диалогов: error-label + Save/Cancel кнопки."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        """Создать пустой диалог с заголовком; наследник наполняет лэйаут через :meth:`_layout`."""
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)

    def _wrap(self, body: QFormLayout | QVBoxLayout) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)
        if isinstance(body, QFormLayout):
            outer.addLayout(body)
        else:
            outer.addLayout(body)
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
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

    def _on_accept(self) -> None:
        try:
            self._validate()
        except ValidationError as exc:
            self._error_label.setText(str(exc))
            return
        self.accept()

    def _validate(self) -> None:
        raise NotImplementedError


class CreateUserDialog(_BaseDialog):
    """Диалог создания пользователя: логин + пароль + опциональные роли."""

    def __init__(self, roles: list[Role], parent: QWidget | None = None) -> None:
        """Принять список доступных ролей для multi-select."""
        super().__init__("Новый пользователь", parent)
        self._login_input = QLineEdit()
        self._password_input = QLineEdit()
        self._password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._password_input.setPlaceholderText(f"минимум {_MIN_PASSWORD_LEN} символа")
        self._roles_list = QListWidget()
        self._roles_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for role in roles:
            item = QListWidgetItem(role.name, self._roles_list)
            item.setData(Qt.ItemDataRole.UserRole, role.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(self._label("Логин"), self._login_input)
        form.addRow(self._label("Пароль"), self._password_input)
        form.addRow(self._label("Роли"), self._roles_list)
        self._wrap(form)

    def values(self) -> tuple[str, str, list[int]]:
        """Вернуть ``(login, password, role_ids)`` после успешной валидации."""
        return (
            self._login_input.text().strip(),
            self._password_input.text(),
            self._collect_role_ids(),
        )

    def _collect_role_ids(self) -> list[int]:
        result: list[int] = []
        for i in range(self._roles_list.count()):
            item = self._roles_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(int(item.data(Qt.ItemDataRole.UserRole)))
        return result

    def _validate(self) -> None:
        if not self._login_input.text().strip():
            raise ValidationError("Логин не может быть пустым")
        if len(self._password_input.text()) < _MIN_PASSWORD_LEN:
            raise ValidationError(f"Пароль должен быть не короче {_MIN_PASSWORD_LEN} символов")

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl


class PasswordResetDialog(_BaseDialog):
    """Сброс пароля: новый + подтверждение."""

    def __init__(self, login: str, parent: QWidget | None = None) -> None:
        """Принять логин для отображения в заголовке."""
        super().__init__(f"Сброс пароля — {login}", parent)
        self._new = QLineEdit()
        self._new.setEchoMode(QLineEdit.EchoMode.Password)
        self._new.setPlaceholderText(f"минимум {_MIN_PASSWORD_LEN} символа")
        self._confirm = QLineEdit()
        self._confirm.setEchoMode(QLineEdit.EchoMode.Password)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(self._label("Новый пароль"), self._new)
        form.addRow(self._label("Подтверждение"), self._confirm)
        self._wrap(form)

    def password(self) -> str:
        """Вернуть валидированный новый пароль."""
        return self._new.text()

    def _validate(self) -> None:
        if len(self._new.text()) < _MIN_PASSWORD_LEN:
            raise ValidationError(f"Пароль должен быть не короче {_MIN_PASSWORD_LEN} символов")
        if self._new.text() != self._confirm.text():
            raise ValidationError("Пароли не совпадают")

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl


class RoleEditDialog(_BaseDialog):
    """Создание/переименование роли: имя + описание."""

    def __init__(
        self,
        title: str,
        *,
        name: str = "",
        description: str = "",
        parent: QWidget | None = None,
    ) -> None:
        """Принять заголовок и опциональные текущие значения для редактирования."""
        super().__init__(title, parent)
        self._name = QLineEdit(name)
        self._description = QLineEdit(description)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow(self._label("Имя роли"), self._name)
        form.addRow(self._label("Описание"), self._description)
        self._wrap(form)

    def values(self) -> tuple[str, str]:
        """Вернуть ``(name, description)``."""
        return self._name.text().strip(), self._description.text().strip()

    def _validate(self) -> None:
        if not self._name.text().strip():
            raise ValidationError("Имя роли не может быть пустым")

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("FieldLabel")
        return lbl


class AssignRolesDialog(_BaseDialog):
    """Назначение ролей пользователю: чекбокс-список текущих и доступных."""

    def __init__(
        self,
        login: str,
        all_roles: list[Role],
        current_role_ids: set[int],
        parent: QWidget | None = None,
    ) -> None:
        """Принять логин (для заголовка), все роли и текущие отмеченные."""
        super().__init__(f"Роли — {login}", parent)
        self._list = QListWidget()
        self._list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        for role in all_roles:
            display = role.name + (" (системная)" if role.is_system else "")
            item = QListWidgetItem(display, self._list)
            item.setData(Qt.ItemDataRole.UserRole, role.id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if role.id in current_role_ids else Qt.CheckState.Unchecked
            )

        body = QVBoxLayout()
        body.setSpacing(8)
        hint = QLabel("Отметьте роли, которые должны быть у пользователя:")
        hint.setObjectName("Muted")
        body.addWidget(hint)
        body.addWidget(self._list)
        self._wrap(body)

    def selected_role_ids(self) -> set[int]:
        """Вернуть множество отмеченных id ролей."""
        result: set[int] = set()
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.add(int(item.data(Qt.ItemDataRole.UserRole)))
        return result

    def _validate(self) -> None:
        return  # любой набор валиден


__all__ = [
    "AssignRolesDialog",
    "CreateUserDialog",
    "PasswordResetDialog",
    "RoleEditDialog",
]


# silence unused import warnings for re-exports
_ = (PrimaryButton, SecondaryButton)
