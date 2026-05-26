"""Тренировки и посещаемость."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.club import Group
    from app.models.people import Tourist, Trainer


class TrainingSession(Base):
    """Конкретное проведённое или запланированное занятие."""

    __tablename__ = "training_session"
    __table_args__ = (CheckConstraint("duration_min > 0", name="duration_min"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id", ondelete="CASCADE"))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainer.person_id", ondelete="RESTRICT"))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_min: Mapped[int]
    location: Mapped[str] = mapped_column(String(160))
    activity_type: Mapped[str] = mapped_column(String(80))

    group: Mapped[Group] = relationship()
    trainer: Mapped[Trainer] = relationship()
    attendances: Mapped[list[Attendance]] = relationship(back_populates="training_session")


class Attendance(Base):
    """Отметка о присутствии туриста на тренировке."""

    __tablename__ = "attendance"

    training_session_id: Mapped[int] = mapped_column(
        ForeignKey("training_session.id", ondelete="CASCADE"), primary_key=True
    )
    tourist_id: Mapped[int] = mapped_column(
        ForeignKey("tourist.person_id", ondelete="CASCADE"), primary_key=True
    )
    present: Mapped[bool] = mapped_column(default=False, server_default="false")

    training_session: Mapped[TrainingSession] = relationship(back_populates="attendances")
    tourist: Mapped[Tourist] = relationship()
