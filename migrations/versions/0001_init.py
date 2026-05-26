"""Init schema: все доменные и системные таблицы.

Revision ID: 0001
Revises:
Create Date: 2026-05-26
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Создать схему БД с нуля."""
    # --- Справочники / независимые таблицы ---
    op.create_table(
        "person",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("middle_name", sa.String(80), nullable=True),
        sa.Column("sex", sa.String(1), nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.CheckConstraint("sex IN ('M','F')", name="ck_person_sex"),
        sa.CheckConstraint("birth_date < CURRENT_DATE", name="ck_person_birth_date"),
    )

    op.create_table(
        "difficulty",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("min_length_km", sa.Numeric(8, 2), nullable=False),
        sa.Column("min_days", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
    )

    op.create_table(
        "competition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("held_at", sa.Date(), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("discipline", sa.String(80), nullable=False),
    )

    op.create_table(
        "route",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False, unique=True),
        sa.Column("length_km", sa.Numeric(8, 2), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.CheckConstraint("length_km > 0", name="ck_route_length_km"),
        sa.CheckConstraint(
            "kind IN ('hike','horse','water','mountain')", name="ck_route_kind"
        ),
    )

    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "permission",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
    )

    # --- Зависят от person ---
    op.create_table(
        "section_head",
        sa.Column("person_id", sa.Integer(), primary_key=True),
        sa.Column("salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name="fk_section_head_person", ondelete="CASCADE"
        ),
        sa.CheckConstraint("salary >= 0", name="ck_section_head_salary"),
    )

    op.create_table(
        "section",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("head_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["head_id"],
            ["section_head.person_id"],
            name="fk_section_head_id",
            ondelete="RESTRICT",
        ),
    )

    op.create_table(
        "trainer",
        sa.Column("person_id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("hire_date", sa.Date(), nullable=False),
        sa.Column("specialization", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name="fk_trainer_person", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["section_id"], ["section.id"], name="fk_trainer_section", ondelete="RESTRICT"
        ),
        sa.CheckConstraint("salary >= 0", name="ck_trainer_salary"),
    )

    op.create_table(
        "tourist",
        sa.Column("person_id", sa.Integer(), primary_key=True),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column("joined_at", sa.Date(), nullable=False),
        sa.Column("can_swim", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("sport_rank", sa.String(40), nullable=True),
        sa.Column("specialization", sa.String(80), nullable=True),
        sa.Column("max_passed_difficulty_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name="fk_tourist_person", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["max_passed_difficulty_id"],
            ["difficulty.id"],
            name="fk_tourist_max_passed_difficulty",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint(
            "category IN ('amateur','athlete','trainer')", name="ck_tourist_category"
        ),
    )

    op.create_table(
        "group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.ForeignKeyConstraint(
            ["section_id"], ["section.id"], name="fk_group_section", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.person_id"],
            name="fk_group_trainer",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("section_id", "name", name="uq_group_section_id_name"),
    )

    op.create_table(
        "group_membership",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("tourist_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.Date(), nullable=False),
        sa.Column("left_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(
            ["group_id"], ["group.id"], name="fk_group_membership_group", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["tourist_id"],
            ["tourist.person_id"],
            name="fk_group_membership_tourist",
            ondelete="CASCADE",
        ),
    )
    # Один активный участник на (группу, туриста); перезайти после выхода — можно.
    op.create_index(
        "uq_group_membership_active",
        "group_membership",
        ["group_id", "tourist_id"],
        unique=True,
        postgresql_where=sa.text("left_at IS NULL"),
    )

    op.create_table(
        "training_session",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_min", sa.Integer(), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("activity_type", sa.String(80), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["group.id"], name="fk_training_session_group", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainer.person_id"],
            name="fk_training_session_trainer",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("duration_min > 0", name="ck_training_session_duration_min"),
    )

    op.create_table(
        "attendance",
        sa.Column("training_session_id", sa.Integer(), primary_key=True),
        sa.Column("tourist_id", sa.Integer(), primary_key=True),
        sa.Column("present", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(
            ["training_session_id"],
            ["training_session.id"],
            name="fk_attendance_training_session",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tourist_id"],
            ["tourist.person_id"],
            name="fk_attendance_tourist",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "competition_participation",
        sa.Column("competition_id", sa.Integer(), primary_key=True),
        sa.Column("person_id", sa.Integer(), primary_key=True),
        sa.Column("result", sa.String(120), nullable=True),
        sa.Column("place", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["competition_id"],
            ["competition.id"],
            name="fk_competition_participation_competition",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["person.id"],
            name="fk_competition_participation_person",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "place IS NULL OR place > 0", name="ck_competition_participation_place"
        ),
    )

    op.create_table(
        "route_point",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("order_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.ForeignKeyConstraint(
            ["route_id"], ["route.id"], name="fk_route_point_route", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("route_id", "order_no", name="uq_route_point_route_id_order_no"),
        sa.UniqueConstraint("route_id", "name", name="uq_route_point_route_id_name"),
        sa.CheckConstraint("order_no >= 1", name="ck_route_point_order_no"),
    )

    op.create_table(
        "trip",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("instructor_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("days_count", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("difficulty_id", sa.Integer(), nullable=False),
        sa.Column("parent_trip_id", sa.Integer(), nullable=True),
        sa.Column(
            "status", sa.String(16), nullable=False, server_default=sa.text("'scheduled'")
        ),
        sa.ForeignKeyConstraint(
            ["route_id"], ["route.id"], name="fk_trip_route", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["instructor_id"],
            ["person.id"],
            name="fk_trip_instructor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["difficulty_id"],
            ["difficulty.id"],
            name="fk_trip_difficulty",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["parent_trip_id"], ["trip.id"], name="fk_trip_parent", ondelete="SET NULL"
        ),
        sa.CheckConstraint("days_count > 0", name="ck_trip_days_count"),
        sa.CheckConstraint("kind IN ('planned','unplanned')", name="ck_trip_kind"),
        sa.CheckConstraint(
            "status IN ('scheduled','in_progress','completed','cancelled')",
            name="ck_trip_status",
        ),
    )

    op.create_table(
        "trip_plan_day",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("day_no", sa.Integer(), nullable=False),
        sa.Column("rest_stops", sa.String(500), nullable=True),
        sa.Column("camp_locations", sa.String(500), nullable=True),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trip.id"], name="fk_trip_plan_day_trip", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("trip_id", "day_no", name="uq_trip_plan_day_trip_id_day_no"),
        sa.CheckConstraint("day_no >= 1", name="ck_trip_plan_day_day_no"),
    )

    op.create_table(
        "trip_diary_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("day_no", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trip.id"], name="fk_trip_diary_entry_trip", ondelete="CASCADE"
        ),
        sa.CheckConstraint("day_no >= 1", name="ck_trip_diary_entry_day_no"),
    )

    op.create_table(
        "trip_participant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("person_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["trip_id"], ["trip.id"], name="fk_trip_participant_trip", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["person.id"],
            name="fk_trip_participant_person",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "trip_id", "person_id", name="uq_trip_participant_trip_id_person_id"
        ),
    )

    op.create_table(
        "app_user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("login", sa.String(80), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("person_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_successful_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["person_id"], ["person.id"], name="fk_app_user_person", ondelete="SET NULL"
        ),
    )

    op.create_table(
        "role_permission",
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.Column("permission_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name="fk_role_permission_role", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permission.id"],
            name="fk_role_permission_permission",
            ondelete="CASCADE",
        ),
    )

    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name="fk_user_role_user", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["role.id"], name="fk_user_role_role", ondelete="CASCADE"
        ),
    )

    op.create_table(
        "audit_login",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("login_attempted", sa.String(80), nullable=False),
        sa.Column(
            "event_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.id"], name="fk_audit_login_user", ondelete="SET NULL"
        ),
    )


def downgrade() -> None:
    """Полный снос схемы (обратный порядок зависимостей)."""
    for table in (
        "audit_login",
        "user_role",
        "role_permission",
        "app_user",
        "trip_participant",
        "trip_diary_entry",
        "trip_plan_day",
        "trip",
        "route_point",
        "competition_participation",
        "attendance",
        "training_session",
        "group_membership",
        "group",
        "tourist",
        "trainer",
        "section",
        "section_head",
        "permission",
        "role",
        "route",
        "competition",
        "difficulty",
        "person",
    ):
        op.drop_table(table)
