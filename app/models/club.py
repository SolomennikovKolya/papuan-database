"""Структура клуба: секции, группы и их участники."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.people import SectionHead, Tourist, Trainer


class Section(Base):
    """Секция клуба."""

    __tablename__ = "section"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    head_id: Mapped[int] = mapped_column(ForeignKey("section_head.person_id", ondelete="RESTRICT"))

    head: Mapped[SectionHead] = relationship(back_populates="sections")
    groups: Mapped[list[Group]] = relationship(back_populates="section")
    trainers: Mapped[list[Trainer]] = relationship(back_populates="section")


class Group(Base):
    """Учебная группа внутри секции."""

    __tablename__ = "group"
    __table_args__ = (UniqueConstraint("section_id", "name", name="section_id_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("section.id", ondelete="RESTRICT"))
    trainer_id: Mapped[int] = mapped_column(ForeignKey("trainer.person_id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120))

    section: Mapped[Section] = relationship(back_populates="groups")
    trainer: Mapped[Trainer] = relationship()
    memberships: Mapped[list[GroupMembership]] = relationship(back_populates="group")


class GroupMembership(Base):
    """Принадлежность туриста к группе с историей вступления/выхода."""

    __tablename__ = "group_membership"
    __table_args__ = (
        # Один активный участник на (группу, туриста). Перезайти после выхода — можно.
        Index(
            "uq_group_membership_active",
            "group_id",
            "tourist_id",
            unique=True,
            postgresql_where="left_at IS NULL",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id", ondelete="CASCADE"))
    tourist_id: Mapped[int] = mapped_column(ForeignKey("tourist.person_id", ondelete="CASCADE"))
    joined_at: Mapped[date]
    left_at: Mapped[date | None]

    group: Mapped[Group] = relationship(back_populates="memberships")
    tourist: Mapped[Tourist] = relationship()
