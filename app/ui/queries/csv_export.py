"""Экспорт таблицы результата запроса в CSV."""

from __future__ import annotations

import csv
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from app.ui.queries.descriptor import ResultColumn


def export_to_csv(path: Path, columns: list[ResultColumn], rows: list[dict[str, Any]]) -> None:
    """Записать строки в ``path`` (UTF-8 с BOM — открывается в Excel «как есть»)."""
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([c.title for c in columns])
        for row in rows:
            writer.writerow([_format(row.get(c.key), c) for c in columns])


def _format(value: Any, column: ResultColumn) -> str:
    if value is None:
        return ""
    if column.formatter:
        return str(column.formatter(value))
    return str(value)
