"""Люди: общая карточка person и профили tourist/trainer/section_head."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.club import Section
    from app.models.trips import Difficulty


class Person(Base):
    """Физическое лицо. Все профили (`tourist`, `trainer`, `section_head`) ссылаются на него."""

    __tablename__ = "person"
    __table_args__ = (
        CheckConstraint("sex IN ('M','F')", name="sex"),
        CheckConstraint("birth_date < CURRENT_DATE", name="birth_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    last_name: Mapped[str] = mapped_column(String(80))
    first_name: Mapped[str] = mapped_column(String(80))
    middle_name: Mapped[str | None] = mapped_column(String(80))
    sex: Mapped[str] = mapped_column(String(1))
    birth_date: Mapped[date] = mapped_column(Date)

    tourist: Mapped[Tourist | None] = relationship(back_populates="person", uselist=False)
    trainer: Mapped[Trainer | None] = relationship(back_populates="person", uselist=False)
    section_head: Mapped[SectionHead | None] = relationship(back_populates="person", uselist=False)


class Tourist(Base):
    """Профиль туриста (1-к-1 с person)."""

    __tablename__ = "tourist"
    __table_args__ = (
        CheckConstraint("category IN ('amateur','athlete','trainer')", name="category"),
    )

    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    category: Mapped[str] = mapped_column(String(16))
    joined_at: Mapped[date] = mapped_column(Date)
    can_swim: Mapped[bool] = mapped_column(default=False, server_default="false")
    sport_rank: Mapped[str | None] = mapped_column(String(40))
    specialization: Mapped[str | None] = mapped_column(String(80))
    max_passed_difficulty_id: Mapped[int | None] = mapped_column(
        ForeignKey("difficulty.id", ondelete="SET NULL")
    )

    person: Mapped[Person] = relationship(back_populates="tourist")
    max_passed_difficulty: Mapped[Difficulty | None] = relationship()


class Trainer(Base):
    """Рабочая карточка тренера (1-к-1 с person)."""

    __tablename__ = "trainer"
    __table_args__ = (CheckConstraint("salary >= 0", name="salary"),)

    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    section_id: Mapped[int] = mapped_column(ForeignKey("section.id", ondelete="RESTRICT"))
    salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    hire_date: Mapped[date] = mapped_column(Date)
    specialization: Mapped[str] = mapped_column(String(80))

    person: Mapped[Person] = relationship(back_populates="trainer")
    section: Mapped[Section] = relationship(back_populates="trainers")


class SectionHead(Base):
    """Рабочая карточка руководителя секции (1-к-1 с person)."""

    __tablename__ = "section_head"
    __table_args__ = (CheckConstraint("salary >= 0", name="salary"),)

    person_id: Mapped[int] = mapped_column(
        ForeignKey("person.id", ondelete="CASCADE"), primary_key=True
    )
    salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    hire_date: Mapped[date] = mapped_column(Date)

    person: Mapped[Person] = relationship(back_populates="section_head")
    sections: Mapped[list[Section]] = relationship(back_populates="head")
