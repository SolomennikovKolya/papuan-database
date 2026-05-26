"""Маршруты, категории сложности, походы."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.people import Person


class Difficulty(Base):
    """Категория сложности похода (справочник)."""

    __tablename__ = "difficulty"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    min_length_km: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    min_days: Mapped[int]
    sort_order: Mapped[int]


class Route(Base):
    """Маршрут похода."""

    __tablename__ = "route"
    __table_args__ = (
        CheckConstraint("length_km > 0", name="length_km"),
        CheckConstraint("kind IN ('hike','horse','water','mountain')", name="kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    length_km: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    kind: Mapped[str] = mapped_column(String(16))

    points: Mapped[list[RoutePoint]] = relationship(
        back_populates="route", order_by="RoutePoint.order_no"
    )


class RoutePoint(Base):
    """Контрольная точка маршрута."""

    __tablename__ = "route_point"
    __table_args__ = (
        UniqueConstraint("route_id", "order_no", name="route_id_order_no"),
        UniqueConstraint("route_id", "name", name="route_id_name"),
        CheckConstraint("order_no >= 1", name="order_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("route.id", ondelete="CASCADE"))
    order_no: Mapped[int]
    name: Mapped[str] = mapped_column(String(160))

    route: Mapped[Route] = relationship(back_populates="points")


class Trip(Base):
    """Поход — конкретное прохождение маршрута."""

    __tablename__ = "trip"
    __table_args__ = (
        CheckConstraint("days_count > 0", name="days_count"),
        CheckConstraint("kind IN ('planned','unplanned')", name="kind"),
        CheckConstraint(
            "status IN ('scheduled','in_progress','completed','cancelled')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("route.id", ondelete="RESTRICT"))
    instructor_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="RESTRICT"))
    start_date: Mapped[date] = mapped_column(Date)
    days_count: Mapped[int]
    kind: Mapped[str] = mapped_column(String(16))
    difficulty_id: Mapped[int] = mapped_column(ForeignKey("difficulty.id", ondelete="RESTRICT"))
    parent_trip_id: Mapped[int | None] = mapped_column(ForeignKey("trip.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="scheduled", server_default="scheduled")

    route: Mapped[Route] = relationship()
    instructor: Mapped[Person] = relationship()
    difficulty: Mapped[Difficulty] = relationship()
    plan_days: Mapped[list[TripPlanDay]] = relationship(back_populates="trip")
    diary_entries: Mapped[list[TripDiaryEntry]] = relationship(back_populates="trip")
    participants: Mapped[list[TripParticipant]] = relationship(back_populates="trip")


class TripPlanDay(Base):
    """План одного дня планового похода (привалы, стоянки)."""

    __tablename__ = "trip_plan_day"
    __table_args__ = (
        UniqueConstraint("trip_id", "day_no", name="trip_id_day_no"),
        CheckConstraint("day_no >= 1", name="day_no"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip.id", ondelete="CASCADE"))
    day_no: Mapped[int]
    rest_stops: Mapped[str | None] = mapped_column(String(500))
    camp_locations: Mapped[str | None] = mapped_column(String(500))

    trip: Mapped[Trip] = relationship(back_populates="plan_days")


class TripDiaryEntry(Base):
    """Запись в дневнике планового похода."""

    __tablename__ = "trip_diary_entry"
    __table_args__ = (CheckConstraint("day_no >= 1", name="day_no"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip.id", ondelete="CASCADE"))
    day_no: Mapped[int]
    content: Mapped[str]
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    trip: Mapped[Trip] = relationship(back_populates="diary_entries")


class TripParticipant(Base):
    """Участник похода (включая инструктора)."""

    __tablename__ = "trip_participant"
    __table_args__ = (UniqueConstraint("trip_id", "person_id", name="trip_id_person_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trip.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="RESTRICT"))

    trip: Mapped[Trip] = relationship(back_populates="participants")
    person: Mapped[Person] = relationship()
