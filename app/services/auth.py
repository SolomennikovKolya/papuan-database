"""Аутентификация: проверка пароля, журнал входов, блокировка.

Сервис принимает уже открытую SQLAlchemy-сессию и не управляет её транзакцией —
**но** журнал ``audit_login`` нужно сохранять даже при отказе во входе
(иначе блокировка по числу неудач никогда не сработает). Поэтому каллер обязан
коммитить сессию **в любом случае** (см. пример в docstring :meth:`AuthService.authenticate`).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import func, select

from app.core.errors import AuthenticationError
from app.models import AppUser, AuditLogin
from app.services.acl import SUPERADMIN_ROLE, AuthContext

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_log = logging.getLogger(__name__)


class AuthService:
    """Логин, выход, смена пароля, журнал входов."""

    MAX_FAILURES = 5
    LOCKOUT_MINUTES = 5

    def __init__(self, session: Session) -> None:
        """Привязать сервис к открытой сессии. Hasher создаётся один раз — он stateless."""
        self._session = session
        self._hasher = PasswordHasher()

    def authenticate(
        self,
        login: str,
        password: str,
        *,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthContext:
        """Проверить логин/пароль и вернуть :class:`AuthContext`.

        Бросает :class:`AuthenticationError` при любой неудаче, при этом запись
        в ``audit_login`` уже добавлена в сессию. **Каллер обязан** закоммитить
        сессию и в случае успеха, и в случае исключения, чтобы лог сохранился::

            session = SessionFactory()
            try:
                ctx = AuthService(session).authenticate(login, pwd)
            finally:
                session.commit()
                session.close()
        """
        user = self._session.execute(
            select(AppUser).where(AppUser.login == login)
        ).scalar_one_or_none()

        if self._is_locked_out(login):
            self._record_attempt(None, login, success=False, ip=ip_address, ua=user_agent)
            raise AuthenticationError(
                f"Слишком много неудачных попыток. Подождите {self.LOCKOUT_MINUTES} мин."
            )

        if user is None:
            self._record_attempt(None, login, success=False, ip=ip_address, ua=user_agent)
            raise AuthenticationError("Неверный логин или пароль")

        if not user.is_active:
            self._record_attempt(user.id, login, success=False, ip=ip_address, ua=user_agent)
            raise AuthenticationError("Учётная запись заблокирована")

        try:
            self._hasher.verify(user.password_hash, password)
        except (VerifyMismatchError, InvalidHashError):
            self._record_attempt(user.id, login, success=False, ip=ip_address, ua=user_agent)
            raise AuthenticationError("Неверный логин или пароль") from None

        if self._hasher.check_needs_rehash(user.password_hash):
            user.password_hash = self._hasher.hash(password)

        user.last_successful_login_at = datetime.now(UTC)
        self._record_attempt(user.id, login, success=True, ip=ip_address, ua=user_agent)
        self._session.flush()

        _log.info("Успешный вход: user_id=%s login=%s", user.id, login)
        return self._build_context(user)

    def change_password(self, user: AppUser, new_password: str) -> None:
        """Сменить пароль пользователя (без проверки старого — это уже отдельный сервис)."""
        user.password_hash = self._hasher.hash(new_password)
        self._session.flush()

    def hash_password(self, password: str) -> str:
        """Вернуть argon2-хеш пароля (utility — пригождается в фикстурах и сервисах)."""
        return self._hasher.hash(password)

    def _is_locked_out(self, login: str) -> bool:
        since = datetime.now(UTC) - timedelta(minutes=self.LOCKOUT_MINUTES)
        recent_failures = self._session.execute(
            select(func.count())
            .select_from(AuditLogin)
            .where(
                AuditLogin.login_attempted == login,
                AuditLogin.success.is_(False),
                AuditLogin.event_at >= since,
            )
        ).scalar_one()
        return int(recent_failures) >= self.MAX_FAILURES

    def _record_attempt(
        self,
        user_id: int | None,
        login: str,
        *,
        success: bool,
        ip: str | None,
        ua: str | None,
    ) -> None:
        entry = AuditLogin(
            user_id=user_id,
            login_attempted=login,
            success=success,
            ip_address=ip,
            user_agent=ua,
        )
        self._session.add(entry)

    def _build_context(self, user: AppUser) -> AuthContext:
        roles = list(user.roles)
        is_super = any(r.name == SUPERADMIN_ROLE for r in roles)
        permissions = frozenset(p.code for r in roles for p in r.permissions)
        return AuthContext(
            user_id=user.id,
            login=user.login,
            is_superadmin=is_super,
            permissions=permissions,
        )
