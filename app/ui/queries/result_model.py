"""Qt-модель таблицы для результатов запросов (словари вместо ORM-объектов)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

if TYPE_CHECKING:
    from app.ui.queries.descriptor import ResultColumn


_BLANK = "—"


class ResultTableModel(QAbstractTableModel):
    """Таблица из списка ``dict``-строк по списку :class:`ResultColumn`."""

    def __init__(self, columns: list[ResultColumn]) -> None:
        """Принять описание колонок; данные задаются через :meth:`set_rows`."""
        super().__init__()
        self._columns = columns
        self._rows: list[dict[str, Any]] = []

    # ---- public api ----
    def set_rows(self, rows: list[dict[str, Any]]) -> None:
        """Полностью заменить отображаемые строки."""
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def row_count(self) -> int:
        """Текущее число строк."""
        return len(self._rows)

    # ---- QAbstractTableModel ----
    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Вернуть число строк."""
        _ = parent
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802
        """Вернуть число колонок."""
        _ = parent
        return len(self._columns)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Вернуть значение/выравнивание для ячейки."""
        if not index.isValid():
            return None
        column = self._columns[index.column()]
        row = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            value = row.get(column.key)
            if value is None:
                return _BLANK
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
        """Вернуть заголовок колонки/номер строки."""
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._columns[section].title
        return section + 1
