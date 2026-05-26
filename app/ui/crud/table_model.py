"""Qt-модель таблицы для дженерик-CRUD: рендерит список ORM-объектов."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

if TYPE_CHECKING:
    from app.models.base import Base
    from app.ui.crud.descriptor import Column


_DEFAULT_BLANK = "—"


def _resolve_path(obj: object, path: str) -> Any:
    """Получить значение по «пути через точку» (``"section.name"``)."""
    current: Any = obj
    for part in path.split("."):
        if current is None:
            return None
        current = getattr(current, part, None)
    return current


class EntityTableModel(QAbstractTableModel):
    """Таблица из ORM-объектов по списку :class:`Column`."""

    def __init__(self, columns: list[Column], items: list[Base] | None = None) -> None:
        """Принять описание колонок и (опционально) начальный список объектов."""
        super().__init__()
        self._columns = columns
        self._items: list[Base] = list(items or [])

    # ---- public api ----
    def set_items(self, items: list[Base]) -> None:
        """Полностью заменить список отображаемых объектов."""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def item_at(self, row: int) -> Base | None:
        """Вернуть объект для конкретной строки или ``None`` для пустой/некорректной."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    # ---- QAbstractTableModel ----
    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Вернуть число строк (один объект — одна строка)."""
        return len(self._items)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Вернуть число колонок."""
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Вернуть значение ячейки для роли отображения/выравнивания."""
        if not index.isValid():
            return None
        column = self._columns[index.column()]
        obj = self._items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            value = _resolve_path(obj, column.field)
            if value is None:
                return _DEFAULT_BLANK
            return column.formatter(value) if column.formatter else str(value)
        if role == Qt.ItemDataRole.TextAlignmentRole:
            mapping = {
                "left": Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                "right": Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                "center": Qt.AlignmentFlag.AlignCenter,
            }
            return int(mapping.get(column.align, mapping["left"]))
        return None

    def headerData(  # noqa: N802
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Вернуть заголовок колонки или номер строки."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section].title
        return section + 1
