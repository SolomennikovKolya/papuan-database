"""Локальная история SQL-запросов: JSON-файл в каталоге пользователя.

Используется SQL-консолью (см. :class:`~app.ui.sql_console.SqlConsoleView`),
чтобы между запусками сохранять последние запросы и режим, в котором они
выполнялись. Хранилище — пользовательское (``platformdirs``), на разных
машинах истории не пересекаются.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import user_data_dir

if TYPE_CHECKING:
    from collections.abc import Iterable

_log = logging.getLogger(__name__)

_DEFAULT_MAX_ENTRIES = 50


@dataclass(frozen=True)
class HistoryEntry:
    """Одна запись истории."""

    sql: str
    mode: str  # "readonly" | "full"
    at: str  # ISO-8601


def default_history_path() -> Path:
    """Каталог пользователя для истории, кросс-платформенно."""
    return Path(user_data_dir("tourist-club", "papuan-db")) / "sql_history.json"


class QueryHistory:
    """Хранит до ``max_entries`` последних запросов в JSON-файле."""

    def __init__(self, path: Path | None = None, max_entries: int = _DEFAULT_MAX_ENTRIES) -> None:
        """Принять путь хранилища (по умолчанию — пользовательский) и лимит записей."""
        self._path = path or default_history_path()
        self._max = max_entries
        self._entries: list[HistoryEntry] = self._load()

    # ---- public api ----
    def add(self, sql: str, mode: str) -> None:
        """Добавить новый запрос в начало (дубль с последним игнорируется)."""
        sql = sql.strip()
        if not sql:
            return
        if self._entries and self._entries[0].sql == sql and self._entries[0].mode == mode:
            return
        entry = HistoryEntry(sql=sql, mode=mode, at=datetime.now(UTC).isoformat())
        self._entries.insert(0, entry)
        del self._entries[self._max :]
        self._save()

    def entries(self) -> list[HistoryEntry]:
        """Все записи (новые — впереди)."""
        return list(self._entries)

    def clear(self) -> None:
        """Полностью очистить историю."""
        self._entries.clear()
        self._save()

    # ---- private ----
    def _load(self) -> list[HistoryEntry]:
        if not self._path.exists():
            return []
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _log.warning("Не удалось прочитать историю %s — начинаем с пустой", self._path)
            return []
        if not isinstance(raw, list):
            return []
        result: list[HistoryEntry] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            sql = item.get("sql")
            mode = item.get("mode", "readonly")
            at = item.get("at", "")
            if isinstance(sql, str) and sql.strip():
                result.append(HistoryEntry(sql=sql, mode=str(mode), at=str(at)))
        return result[: self._max]

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            payload: Iterable[dict] = (asdict(e) for e in self._entries)
            self._path.write_text(
                json.dumps(list(payload), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            _log.warning("Не удалось сохранить историю %s: %s", self._path, exc)
