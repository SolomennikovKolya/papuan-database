"""Универсальный CRUD-репозиторий для SQLAlchemy 2.0.

Принципы:
- репозиторий не управляет транзакциями (это делает сервис через ``session_scope``);
- работает с моделями, имеющими **одиночный** PK; для композитных PK заводятся
  собственные репозитории-наследники с переопределённой работой по ключу;
- сортировка/фильтр/пагинация — параметры метода :meth:`Repository.list`,
  чтобы один и тот же класс закрывал любые CRUD-экраны.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from app.core.errors import NotFound
from app.models.base import Base

if TYPE_CHECKING:
    from sqlalchemy import ColumnElement
    from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Page[ModelT: Base]:
    """Страница результатов: сами объекты + метаданные пагинации."""

    items: list[ModelT]
    total: int
    offset: int
    limit: int | None


@dataclass(frozen=True)
class Sort:
    """Сортировка по одной колонке модели."""

    field: str
    descending: bool = False

    @classmethod
    def parse(cls, raw: str) -> Sort:
        """Разобрать строку вида ``"name"`` / ``"-name"`` в :class:`Sort`."""
        if raw.startswith("-"):
            return cls(raw[1:], descending=True)
        return cls(raw, descending=False)


class Repository[ModelT: Base]:
    """Базовый репозиторий: CRUD, постраничный список, сортировка, фильтры."""

    def __init__(self, session: Session, model: type[ModelT]) -> None:
        """Связать репозиторий с конкретной сессией и моделью."""
        self._session = session
        self._model = model

    @property
    def session(self) -> Session:
        """Открытая SQLAlchemy-сессия, привязанная к репозиторию."""
        return self._session

    @property
    def model(self) -> type[ModelT]:
        """Класс модели, с которым работает этот репозиторий."""
        return self._model

    def get(self, pk: Any) -> ModelT | None:
        """Найти запись по PK; вернуть ``None``, если не существует."""
        return self._session.get(self._model, pk)

    def get_or_raise(self, pk: Any) -> ModelT:
        """Найти запись по PK или бросить :class:`NotFound`."""
        obj = self.get(pk)
        if obj is None:
            raise NotFound(f"{self._model.__name__} с id={pk!r} не найден")
        return obj

    def list(
        self,
        *,
        where: list[ColumnElement[bool]] | None = None,
        order_by: list[Sort] | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Page[ModelT]:
        """Вернуть страницу записей.

        Args:
            where: список SQLAlchemy-условий; объединяются через ``AND``.
            order_by: список сортировок (применяются по порядку).
            limit: размер страницы (``None`` — без лимита).
            offset: смещение от начала.
        """
        stmt = select(self._model)
        if where:
            stmt = stmt.where(*where)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = int(self._session.execute(count_stmt).scalar_one())

        if order_by:
            stmt = stmt.order_by(*(self._resolve_order(s) for s in order_by))
        if offset:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        items = list(self._session.execute(stmt).scalars().all())
        return Page(items=items, total=total, offset=offset, limit=limit)

    def create(self, **fields: Any) -> ModelT:
        """Создать запись и зафлешить её (без ``commit`` — это дело сервиса)."""
        obj = self._model(**fields)
        self._session.add(obj)
        self._session.flush()
        return obj

    def update(self, obj: ModelT, **changes: Any) -> ModelT:
        """Применить изменения полей к существующему объекту, зафлешить, вернуть."""
        for name, value in changes.items():
            if not hasattr(obj, name):
                raise AttributeError(f"{self._model.__name__} не имеет атрибута {name!r}")
            setattr(obj, name, value)
        self._session.flush()
        return obj

    def delete(self, obj: ModelT) -> None:
        """Удалить объект из БД (без ``commit``)."""
        self._session.delete(obj)
        self._session.flush()

    def delete_by_pk(self, pk: Any) -> None:
        """Удалить по PK; если не найден — :class:`NotFound`."""
        self.delete(self.get_or_raise(pk))

    def _resolve_order(self, sort: Sort) -> Any:
        column = getattr(self._model, sort.field, None)
        if column is None:
            raise ValueError(f"Поле {sort.field!r} отсутствует в модели {self._model.__name__}")
        return column.desc() if sort.descending else column.asc()
