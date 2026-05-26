"""Соревнования и участие в них."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.people import Person


class Competition(Base):
    """Соревнование."""

    __tablename__ = "competition"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    held_at: Mapped[date] = mapped_column(Date)
    location: Mapped[str] = mapped_column(String(160))
    discipline: Mapped[str] = mapped_column(String(80))

    participations: Mapped[list[CompetitionParticipation]] = relationship(
        back_populates="competition"
    )


class CompetitionParticipation(Base):
    """Участие конкретного человека (спортсмена/тренера) в соревновании."""

    __tablename__ = "competition_participation"
    __table_args__ = (CheckConstraint("place IS NULL OR place > 0", name="place"),)

    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competition.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    result: Mapped[str | None] = mapped_column(String(120))
    place: Mapped[int | None]

    competition: Mapped[Competition] = relationship(back_populates="participations")
    person: Mapped[Person] = relationship()
