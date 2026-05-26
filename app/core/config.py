"""Конфигурация приложения.

Все настройки читаются из переменных окружения (или ``.env``-файла рядом
с корнем проекта) через pydantic-settings. Доступ к настройкам — только
через :func:`get_settings`, который кэширует результат и гарантирует, что
парсинг и валидация произойдут ровно один раз за время жизни процесса.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    """Типизированная модель всех конфигурационных параметров приложения.

    Имена полей сопоставляются с переменными окружения без учёта регистра,
    поэтому поле ``db_host`` читается из ``DB_HOST``. См. ``.env.example``
    для актуального списка ключей.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- БД: основной пользователь ---
    db_host: str = "localhost"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_name: str = "tourist_club"
    db_user: str = "tourist_app"
    db_password: SecretStr = SecretStr("change_me_please")

    # --- БД: read-only пользователь для SQL-консоли ---
    db_readonly_user: str = "tourist_ro"
    db_readonly_password: SecretStr = SecretStr("change_me_please_ro")

    # --- Приложение ---
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    app_theme: Literal["light", "dark"] = "light"
    app_default_admin_password: SecretStr = SecretStr("admin")

    @property
    def db_url(self) -> URL:
        """SQLAlchemy URL для основного подключения к БД."""
        return self._build_url(self.db_user, self.db_password)

    @property
    def db_readonly_url(self) -> URL:
        """SQLAlchemy URL для read-only подключения (SQL-консоль)."""
        return self._build_url(self.db_readonly_user, self.db_readonly_password)

    def _build_url(self, user: str, password: SecretStr) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=user,
            password=password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Вернуть синглтон настроек (читается из окружения один раз за процесс)."""
    return Settings()
