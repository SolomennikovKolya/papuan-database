"""Панель управления пользователями: список + действия."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from app.core.errors import AppError
from app.models import AppUser, Role
from app.services import RolesService, UsersService, use
from app.ui.admin.dialogs import (
    AssignRolesDialog,
    CreateUserDialog,
    PasswordResetDialog,
)
from app.ui.crud.descriptor import Column
from app.ui.crud.table_model import EntityTableModel
from app.ui.widgets import PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.acl import AuthContext

_log = logging.getLogger(__name__)


_COLUMNS: list[Column] = [
    Column("id", "ID", width=60, align="right"),
    Column("login", "Логин"),
    Column(
        "is_active",
        "Активен",
        width=90,
        align="center",
        formatter=lambda v: "да" if v else "нет",
    ),
    Column("created_at", "Создан", width=160),
    Column("last_successful_login_at", "Последний вход", width=160),
]


class UsersPanel(QWidget):
    """Список пользователей + кнопки add / block / reset / roles."""

    # ---- init ----
    def __init__(self, session: Session, ctx: AuthContext, parent: QWidget | None = None) -> None:
        """Принять сессию и контекст; список загружается сразу при создании."""
        super().__init__(parent)
        self._session = session
        self._ctx = ctx
        self._users_svc = UsersService(session)
        self._roles_svc = RolesService(session)
        self._model = EntityTableModel(_COLUMNS)
        self._table: QTableView
        self._add_btn: PrimaryButton
        self._block_btn: SecondaryButton
        self._reset_btn: SecondaryButton
        self._roles_btn: SecondaryButton
        self._error_label: QLabel
        self._build_ui()
        self._wire()
        self.refresh()

    # ---- public api ----
    def refresh(self) -> None:
        """Перечитать список пользователей."""
        try:
            with use(self._ctx):
                page = self._users_svc.list(limit=500)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            self._model.set_items([])
            return
        self._model.set_items(list(page.items))
        self._set_error("")
        self._refresh_buttons()

    # ---- slots ----
    @Slot()
    def _on_add(self) -> None:
        roles = self._load_all_roles_non_system()
        dialog = CreateUserDialog(roles=roles, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        login, password, role_ids = dialog.values()
        try:
            with use(self._ctx):
                self._users_svc.create(login, password, role_ids=role_ids)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self.refresh()

    @Slot()
    def _on_toggle_active(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        try:
            with use(self._ctx):
                self._users_svc.set_active(user.id, not user.is_active)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self.refresh()

    @Slot()
    def _on_reset_password(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        dialog = PasswordResetDialog(login=user.login, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            with use(self._ctx):
                self._users_svc.reset_password(user.id, dialog.password())
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        QMessageBox.information(self, "Пароль сброшен", f"Пароль для {user.login!r} обновлён.")

    @Slot()
    def _on_assign_roles(self) -> None:
        user = self._selected_user()
        if user is None:
            return
        all_roles = self._load_all_roles()
        current_ids = {r.id for r in user.roles}
        dialog = AssignRolesDialog(user.login, all_roles, current_ids, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        desired = dialog.selected_role_ids()
        try:
            with use(self._ctx):
                for role_id in desired - current_ids:
                    self._users_svc.assign_role(user.id, role_id)
                for role_id in current_ids - desired:
                    self._users_svc.revoke_role(user.id, role_id)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._set_error(str(exc))
            return
        self.refresh()

    @Slot()
    def _on_selection_changed(self) -> None:
        self._refresh_buttons()

    # ---- private ----
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self._add_btn = PrimaryButton("+ Пользователь")
        self._block_btn = SecondaryButton("Заблокировать")
        self._reset_btn = SecondaryButton("Сбросить пароль")
        self._roles_btn = SecondaryButton("Роли…")
        toolbar.addWidget(self._add_btn)
        toolbar.addWidget(self._block_btn)
        toolbar.addWidget(self._reset_btn)
        toolbar.addWidget(self._roles_btn)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table, 1)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)

    def _wire(self) -> None:
        self._add_btn.clicked.connect(self._on_add)
        self._block_btn.clicked.connect(self._on_toggle_active)
        self._reset_btn.clicked.connect(self._on_reset_password)
        self._roles_btn.clicked.connect(self._on_assign_roles)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def _selected_user(self) -> AppUser | None:
        idx = self._table.currentIndex()
        if not idx.isValid():
            return None
        return self._model.item_at(idx.row())

    def _refresh_buttons(self) -> None:
        user = self._selected_user()
        has = user is not None
        self._block_btn.setEnabled(has)
        self._reset_btn.setEnabled(has)
        self._roles_btn.setEnabled(has)
        if has:
            self._block_btn.setText("Разблокировать" if not user.is_active else "Заблокировать")
        else:
            self._block_btn.setText("Заблокировать")

    def _set_error(self, message: str) -> None:
        self._error_label.setText(message)

    def _load_all_roles(self) -> list[Role]:
        return list(self._session.execute(select(Role).order_by(Role.name)).scalars())

    def _load_all_roles_non_system(self) -> list[Role]:
        return list(
            self._session.execute(
                select(Role).where(Role.is_system.is_(False)).order_by(Role.name)
            ).scalars()
        )
