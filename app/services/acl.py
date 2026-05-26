"""ACL: контекст текущего пользователя и декоратор проверки прав.

Контекст хранится в :class:`ContextVar` — это безопасно для desktop-приложения
(один пользователь на процесс) и удобно для тестов: для прогона метода под
конкретным пользователем достаточно обернуть вызов в ``with use(ctx): ...``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, TypeVar

from app.core.errors import PermissionDenied

SUPERADMIN_ROLE = "superadmin"

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class AuthContext:
    """Снимок сведений о текущем пользователе, нужный для проверки прав.

    Создаётся при успешном входе (см. :mod:`app.services.auth`) и кладётся
    в :data:`_current` через :func:`use`. Имеет неизменяемый снимок прав —
    повторно дергать БД на каждую проверку не нужно.
    """

    user_id: int
    login: str
    is_superadmin: bool
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has(self, permission: str) -> bool:
        """Проверить, есть ли у пользователя данное право."""
        return self.is_superadmin or permission in self.permissions


_current: ContextVar[AuthContext | None] = ContextVar("auth_context", default=None)


def current() -> AuthContext | None:
    """Вернуть текущий :class:`AuthContext` или ``None``, если никто не вошёл."""
    return _current.get()


def require_current() -> AuthContext:
    """Вернуть текущий :class:`AuthContext` или бросить :class:`PermissionDenied`."""
    ctx = _current.get()
    if ctx is None:
        raise PermissionDenied("Действие требует входа в систему")
    return ctx


@contextmanager
def use(ctx: AuthContext | None) -> Iterator[None]:
    """Временно установить ``ctx`` как текущий ACL-контекст (стек, потокобезопасно)."""
    token = _current.set(ctx)
    try:
        yield
    finally:
        _current.reset(token)


def require_permission(permission: str) -> AuthContext:
    """Проверить право у текущего пользователя; бросить :class:`PermissionDenied`.

    Функциональный аналог декоратора :func:`require` — нужен когда имя
    права собирается динамически (например, в дженерик-сервисах).
    """
    ctx = require_current()
    if not ctx.has(permission):
        raise PermissionDenied(f"Нет права {permission!r}")
    return ctx


def require(permission: str) -> Callable[[F], F]:
    """Декоратор: пропускает вызов, только если у текущего пользователя есть ``permission``.

    Иначе бросает :class:`PermissionDenied`. Применяется к методам сервисов
    (не к UI-обработчикам — UI лишь скрывает недоступные кнопки).
    """

    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctx = require_current()
            if not ctx.has(permission):
                raise PermissionDenied(f"Нет права {permission!r}")
            return fn(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
