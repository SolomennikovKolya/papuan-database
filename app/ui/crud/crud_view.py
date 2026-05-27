"""Универсальный CRUD-экран: таблица + поиск + действия.

Один класс закрывает все справочники с одиночным PK; всё, что нужно конкретной
сущности, лежит в :class:`EntityDescriptor`. Пагинация отсутствует — для
учебных объёмов данных таблицы прокручиваются естественным образом.
"""

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
    QLineEdit,
    QMessageBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import String, inspect, or_

from app.core.errors import AppError
from app.core.events import get_bus
from app.repositories import Sort
from app.services import EntityService, use
from app.ui.crud.form_dialog import FormDialog
from app.ui.crud.table_model import EntityTableModel
from app.ui.widgets import PrimaryButton, SecondaryButton

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.models.base import Base
    from app.services.acl import AuthContext
    from app.ui.crud.descriptor import EntityDescriptor

_log = logging.getLogger(__name__)


class CrudView(QWidget):
    """Экран CRUD для одной сущности (полностью управляется ``EntityDescriptor``)."""

    # ---- init ----
    def __init__(
        self,
        descriptor: EntityDescriptor,
        session: Session,
        ctx: AuthContext,
        parent: QWidget | None = None,
    ) -> None:
        """Создать вид. ``session`` живёт столько же, сколько и экран."""
        super().__init__(parent)
        self._descriptor = descriptor
        self._session = session
        self._ctx = ctx
        self._service: EntityService = EntityService(
            session, descriptor.model, descriptor.perm_prefix
        )

        self._search_query = ""
        self._table_model = EntityTableModel(descriptor.columns)
        self._search_input: QLineEdit
        self._add_btn: PrimaryButton
        self._edit_btn: SecondaryButton
        self._delete_btn: SecondaryButton
        self._error_label: QLabel
        self._table_view: QTableView

        # Строковые колонки модели (для поиска, если у дескриптора нет search_field).
        self._search_columns = self._discover_string_columns()

        self._build_ui()
        self._wire()
        self._apply_permissions()
        get_bus().data_invalidated.connect(self._on_data_invalidated)
        self.refresh()

    # ---- public api ----
    def refresh(self) -> None:
        """Перечитать данные из БД и обновить таблицу."""
        try:
            with use(self._ctx):
                # SQLAlchemy кэширует объекты в identity map — сбрасываем,
                # чтобы видеть свежие данные после внешних изменений (seed/truncate).
                self._session.expire_all()
                page = self._service.list(
                    where=self._build_where(),
                    order_by=[Sort.parse(self._descriptor.default_sort)],
                )
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._show_error(str(exc))
            self._table_model.set_items([])
            return

        self._table_model.set_items(page.items)
        self._clear_error()

    # ---- slots ----
    @Slot(str)
    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip()
        self.refresh()

    @Slot()
    def _on_add(self) -> None:
        dialog = FormDialog(
            title=f"Добавить — {self._descriptor.title_singular}",
            fields=self._descriptor.form_fields,
            session=self._session,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            with use(self._ctx):
                self._service.create(**dialog.values())
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._show_error(str(exc))
            return
        get_bus().emit_data_invalidated(self._descriptor.model.__tablename__)
        self.refresh()

    @Slot()
    def _on_edit(self) -> None:
        instance = self._selected_item()
        if instance is None:
            return
        dialog = FormDialog(
            title=f"Изменить — {self._descriptor.title_singular}",
            fields=self._descriptor.form_fields,
            session=self._session,
            instance=instance,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            with use(self._ctx):
                self._service.update(instance, **dialog.values())
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._show_error(str(exc))
            return
        get_bus().emit_data_invalidated(self._descriptor.model.__tablename__)
        self.refresh()

    @Slot()
    def _on_delete(self) -> None:
        instance = self._selected_item()
        if instance is None:
            return
        confirm = QMessageBox.question(
            self,
            "Удалить?",
            f"Удалить выбранную запись из «{self._descriptor.title}»?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            with use(self._ctx):
                self._service.delete(instance)
                self._session.commit()
        except AppError as exc:
            self._session.rollback()
            self._show_error(str(exc))
            return
        get_bus().emit_data_invalidated(self._descriptor.model.__tablename__)
        self.refresh()

    @Slot()
    def _on_selection_changed(self) -> None:
        has_selection = self._selected_item() is not None
        if self._ctx.has(f"{self._descriptor.perm_prefix}.update"):
            self._edit_btn.setEnabled(has_selection)
        if self._ctx.has(f"{self._descriptor.perm_prefix}.delete"):
            self._delete_btn.setEnabled(has_selection)

    @Slot(str)
    def _on_data_invalidated(self, scope: str) -> None:
        # `"*"` означает «всё изменилось» (например, seed/truncate).
        if scope in ("*", self._descriptor.model.__tablename__):
            self.refresh()

    # ---- private ----
    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        title = QLabel(self._descriptor.title)
        title.setObjectName("H1")
        outer.addWidget(title)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self._search_input = QLineEdit()
        self._search_input.setClearButtonEnabled(True)
        labels = self._searchable_labels()
        if labels:
            self._search_input.setPlaceholderText("Поиск по: " + ", ".join(labels))
        else:
            self._search_input.setPlaceholderText("Поиск недоступен")
            self._search_input.setEnabled(False)
        toolbar.addWidget(self._search_input, 1)

        self._add_btn = PrimaryButton("+ Добавить")
        self._edit_btn = SecondaryButton("Изменить")
        self._delete_btn = SecondaryButton("Удалить")
        self._edit_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        toolbar.addWidget(self._add_btn)
        toolbar.addWidget(self._edit_btn)
        toolbar.addWidget(self._delete_btn)

        outer.addLayout(toolbar)

        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.verticalHeader().setVisible(False)
        header = self._table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setHighlightSections(False)
        outer.addWidget(self._table_view, 1)

        self._error_label = QLabel("")
        self._error_label.setObjectName("ErrorLabel")
        self._error_label.setWordWrap(True)
        outer.addWidget(self._error_label)

    def _wire(self) -> None:
        self._search_input.textChanged.connect(self._on_search_changed)
        self._add_btn.clicked.connect(self._on_add)
        self._edit_btn.clicked.connect(self._on_edit)
        self._delete_btn.clicked.connect(self._on_delete)
        self._table_view.selectionModel().selectionChanged.connect(self._on_selection_changed)
        self._table_view.doubleClicked.connect(self._on_edit)

    def _apply_permissions(self) -> None:
        prefix = self._descriptor.perm_prefix
        self._add_btn.setVisible(self._ctx.has(f"{prefix}.create"))
        self._edit_btn.setVisible(self._ctx.has(f"{prefix}.update"))
        self._delete_btn.setVisible(self._ctx.has(f"{prefix}.delete"))

    def _discover_string_columns(self) -> list:
        # SQLAlchemy инспекция: все колонки строкового типа модели.
        mapper = inspect(self._descriptor.model)
        return [c for c in mapper.columns if isinstance(c.type, String)]

    def _searchable_labels(self) -> list[str]:
        """Человекочитаемые названия полей, по которым идёт поиск (для подсказки)."""
        if self._descriptor.search_field:
            field_names = [self._descriptor.search_field]
        else:
            field_names = [c.name for c in self._search_columns]
        title_by_field = {c.field: c.title for c in self._descriptor.columns}
        return [title_by_field.get(name, name) for name in field_names]

    def _build_where(self) -> list:
        clauses: list = []
        if not self._search_query:
            return clauses
        if self._descriptor.search_field:
            column = getattr(self._descriptor.model, self._descriptor.search_field, None)
            if column is not None:
                clauses.append(column.ilike(f"%{self._search_query}%"))
                return clauses
        if self._search_columns:
            clauses.append(or_(*[c.ilike(f"%{self._search_query}%") for c in self._search_columns]))
        return clauses

    def _selected_item(self) -> Base | None:
        idx = self._table_view.currentIndex()
        if not idx.isValid():
            return None
        return self._table_model.item_at(idx.row())

    def _show_error(self, message: str) -> None:
        self._error_label.setText(message)
        _log.warning("CRUD error (%s): %s", self._descriptor.model.__name__, message)

    def _clear_error(self) -> None:
        self._error_label.clear()
