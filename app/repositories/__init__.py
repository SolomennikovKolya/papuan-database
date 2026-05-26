"""Репозитории — единая точка доступа к данным для сервисного слоя."""

from __future__ import annotations

from app.repositories.base import Page, Repository, Sort

__all__ = ["Page", "Repository", "Sort"]
