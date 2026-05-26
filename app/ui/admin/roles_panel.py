"""Панель управления ролями: список + чекбокс-матрица прав."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from app.core.errors import AppError
from app.models import Permission, Role
from app.services import RolesService, use
from app.ui.admin.dialogs import RoleEditDialog
from app.ui.widgets import GhostButton, PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)


class RolesPanel(QWidget):
    """Слева — список ролей; справа — чекбокс-матрица прав по сущностям."""

    # ---- init ----
    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст; загрузить список ролей и матрицу прав."""
        super().__init__(parent)
        self._session = session
        self._ctx = ctx
        self._roles_svc = RolesService(session)
        self._all_permissions: list[Permission] = []
        self._current_role: Role | None = None
        self._checkboxes: dict[str, QCheckBox] = {}

        self._list: QListWidget
        self._add_btn: PrimaryButton
        self._rename_btn: SecondaryButton
        self._delete_btn: SecondaryButton
        self._save_btn: PrimaryButton
        self._error_label: QLabel
        self._matrix_container: QWidget
        self._matrix_layout: QVBoxLayout
        self._role_header: QLabel

        self._build_ui()
        self._wire()
        self.reload()

    # ---- public api ----
    def reload(self) -> None:
        """Перечитать справочник прав и список ролей с БД."""
        try:
            self._all_permissions = list(
                self._session.execute(select(Permission).order_by(Permission.code)).scalars()
            )
            with use(self._ctx):
                page = self._roles_svc.list()
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self._populate_role_list(list(page.items))
        self._rebuild_matrix()
        self._set_error("")

    # ---- slots ----
    @Slot()
    def _on_select_role(self) -> None:
        item = self._list.currentItem()
        if item is None:
            self._current_role = None
        else:
            role_id = int(item.data(Qt.ItemDataRole.UserRole))
            self._current_role = self._session.get(Role, role_id)
        self._rebuild_matrix()
        self._refresh_buttons()

    @Slot()
    def _on_add(self) -> None:
        dialog = RoleEditDialog("Новая роль", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, description = dialog.values()
        try:
            with use(self._ctx):
                self._roles_svc.create(name, description)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self.reload()

    @Slot()
    def _on_rename(self) -> None:
        if self._current_role is None or self._current_role.is_system:
            return
        dialog = RoleEditDialog(
            "Изменить роль",
            name=self._current_role.name,
            description=self._current_role.description or "",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, description = dialog.values()
        try:
            with use(self._ctx):
                self._roles_svc.rename(self._current_role.id, name=name, description=description)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self.reload()

    @Slot()
    def _on_delete(self) -> None:
        if self._current_role is None or self._current_role.is_system:
            return
        confirm = QMessageBox.question(
            self,
            "Удалить роль?",
            f"Удалить роль «{self._current_role.name}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            with use(self._ctx):
                self._roles_svc.delete(self._current_role.id)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self._current_role = None
        self.reload()

    @Slot()
    def _on_save_permissions(self) -> None:
        if self._current_role is None or self._current_role.is_system:
            return
        codes = [code for code, cb in self._checkboxes.items() if cb.isChecked()]
        try:
            with use(self._ctx):
                self._roles_svc.set_permissions(self._current_role.id, codes)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        QMessageBox.information(self, "Сохранено", "Набор прав роли обновлён.")
        self.reload()

    # ---- private ----
    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ---- левая колонка: роли ----
        left = QVBoxLayout()
        left.setSpacing(8)
        left_label = QLabel("Роли")
        left_label.setObjectName("H2")
        left.addWidget(left_label)

        self._list = QListWidget()
        self._list.setMinimumWidth(220)
        left.addWidget(self._list, 1)

        btns = QHBoxLayout()
        self._add_btn = PrimaryButton("+")
        self._add_btn.setToolTip("Создать роль")
        self._rename_btn = SecondaryButton("✎")
        self._rename_btn.setToolTip("Переименовать роль")
        self._delete_btn = SecondaryButton("🗑")
        self._delete_btn.setToolTip("Удалить роль")
        for b in (self._add_btn, self._rename_btn, self._delete_btn):
            btns.addWidget(b)
        btns.addStretch(1)
        left.addLayout(btns)
        root.addLayout(left, 0)

        # ---- правая колонка: матрица прав ----
        right = QVBoxLayout()
        right.setSpacing(8)

        self._role_header = QLabel("Выберите роль слева")
        self._role_header.setObjectName("H2")
        right.addWidget(self._role_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._matrix_container = QWidget()
        self._matrix_layout = QVBoxLayout(self._matrix_container)
        self._matrix_layout.setContentsMargins(0, 0, 0, 0)
        self._matrix_layout.setSpacing(8)
        scroll.setWidget(self._matrix_container)
        right.addWidget(scroll, 1)

        save_row = QHBoxLayout()
        save_row.addStretch(1)
        self._save_btn = PrimaryButton("Сохранить права")
        save_row.addWidget(self._save_btn)
        right.addLayout(save_row)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        right.addWidget(self._error_label)

        root.addLayout(right, 1)

    def _wire(self) -> None:
        self._list.currentItemChanged.connect(lambda *_a: self._on_select_role())
        self._add_btn.clicked.connect(self._on_add)
        self._rename_btn.clicked.connect(self._on_rename)
        self._delete_btn.clicked.connect(self._on_delete)
        self._save_btn.clicked.connect(self._on_save_permissions)

    def _populate_role_list(self, roles: list[Role]) -> None:
        previous_id = self._current_role.id if self._current_role is not None else None
        self._list.clear()
        for role in roles:
            display = role.name + (" (системная)" if role.is_system else "")
            item = QListWidgetItem(display, self._list)
            item.setData(Qt.ItemDataRole.UserRole, role.id)
            if role.id == previous_id:
                self._list.setCurrentItem(item)
        if self._current_role is None and self._list.count() > 0:
            self._list.setCurrentRow(0)

    def _rebuild_matrix(self) -> None:
        # Очистить старые виджеты
        while self._matrix_layout.count():
            child = self._matrix_layout.takeAt(0)
            widget = child.widget()
            if widget is not None:
                widget.deleteLater()
        self._checkboxes.clear()

        if self._current_role is None:
            self._role_header.setText("Выберите роль слева")
            self._refresh_buttons()
            return

        is_system = self._current_role.is_system
        suffix = "  (системная роль — права изменять нельзя)" if is_system else ""
        self._role_header.setText(f"Права: {self._current_role.name}{suffix}")

        current_codes = {p.code for p in self._current_role.permissions}

        # Группировка прав по «entity» (часть до первой точки) — приятнее визуально.
        grouped: dict[str, list[Permission]] = defaultdict(list)
        for perm in self._all_permissions:
            group_key = perm.code.split(".", 1)[0]
            grouped[group_key].append(perm)

        for group_name in sorted(grouped):
            header = QLabel(group_name)
            header.setObjectName("FieldLabel")
            self._matrix_layout.addWidget(header)
            for perm in grouped[group_name]:
                cb = QCheckBox(f"{perm.code} — {perm.description or ''}")
                cb.setChecked(perm.code in current_codes)
                cb.setEnabled(not is_system)
                self._checkboxes[perm.code] = cb
                self._matrix_layout.addWidget(cb)
        self._matrix_layout.addStretch(1)
        self._refresh_buttons()

    def _refresh_buttons(self) -> None:
        has_role = self._current_role is not None
        is_system = self._current_role.is_system if has_role else False
        editable = has_role and not is_system
        self._rename_btn.setEnabled(editable)
        self._delete_btn.setEnabled(editable)
        self._save_btn.setEnabled(editable)

    def _set_error(self, message: str) -> None:
        self._error_label.setText(message)


__all__ = ["RolesPanel"]


# silence unused warnings (re-exported in case future panels need them)
_ = GhostButton
