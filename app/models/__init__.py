"""ORM-модели (SQLAlchemy 2.0, typed declarative).

Реэкспортируем `Base` и все классы — это упрощает импорты в репозиториях
и обеспечивает обнаружение моделей Alembic-ом (``target_metadata``).
"""

from __future__ import annotations

from app.models.base import Base
from app.models.club import Group, GroupMembership, Section
from app.models.competitions import Competition, CompetitionParticipation
from app.models.people import Person, SectionHead, Tourist, Trainer
from app.models.security import (
    AppUser,
    AuditLogin,
    Permission,
    Role,
    RolePermission,
    UserRole,
)
from app.models.training import Attendance, TrainingSession
from app.models.trips import (
    Difficulty,
    Route,
    RoutePoint,
    Trip,
    TripDiaryEntry,
    TripParticipant,
    TripPlanDay,
)

metadata = Base.metadata

__all__ = [
    "AppUser",
    "Attendance",
    "AuditLogin",
    "Base",
    "Competition",
    "CompetitionParticipation",
    "Difficulty",
    "Group",
    "GroupMembership",
    "Permission",
    "Person",
    "Role",
    "RolePermission",
    "Route",
    "RoutePoint",
    "Section",
    "SectionHead",
    "Tourist",
    "Trainer",
    "TrainingSession",
    "Trip",
    "TripDiaryEntry",
    "TripParticipant",
    "TripPlanDay",
    "UserRole",
    "metadata",
]
