"""Триггеры PL/pgSQL: квалификация инструктора, наличие в участниках,
проверка плавания для водных походов, обновление категории туриста.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-26
"""

from __future__ import annotations

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


_UPGRADE_SQL = """
-- ──────────────────────────────────────────────────────────────────────────
-- 1. Инструктор должен иметь опыт похода не меньшей сложности
-- ──────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_trip_instructor_qualified()
RETURNS TRIGGER AS $$
DECLARE
    new_sort_order INT;
    min_sort_order INT;
    has_qualifying BOOLEAN;
BEGIN
    SELECT sort_order INTO new_sort_order
        FROM difficulty WHERE id = NEW.difficulty_id;
    SELECT MIN(sort_order) INTO min_sort_order FROM difficulty;

    -- Самая низкая категория сложности — bootstrap, проверка пропускается.
    IF new_sort_order = min_sort_order THEN
        RETURN NEW;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM trip_participant tp
        JOIN trip t ON t.id = tp.trip_id
        JOIN difficulty d ON d.id = t.difficulty_id
        WHERE tp.person_id = NEW.instructor_id
          AND t.id <> NEW.id
          AND t.status = 'completed'
          AND d.sort_order >= new_sort_order
    ) INTO has_qualifying;

    IF NOT has_qualifying THEN
        RAISE EXCEPTION
            'Инструктор % не имеет опыта похода сложности >= %',
            NEW.instructor_id, new_sort_order
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_trip_instructor_qualified
BEFORE INSERT OR UPDATE OF instructor_id, difficulty_id ON trip
FOR EACH ROW EXECUTE FUNCTION trg_trip_instructor_qualified();

-- ──────────────────────────────────────────────────────────────────────────
-- 2. На водные походы — только умеющие плавать туристы.
--    (Если участник — не турист, проверка пропускается.)
-- ──────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_water_trip_requires_swim()
RETURNS TRIGGER AS $$
DECLARE
    route_kind TEXT;
    can_swim_val BOOLEAN;
BEGIN
    SELECT r.kind INTO route_kind
        FROM trip t JOIN route r ON r.id = t.route_id
        WHERE t.id = NEW.trip_id;

    IF route_kind <> 'water' THEN
        RETURN NEW;
    END IF;

    SELECT can_swim INTO can_swim_val FROM tourist WHERE person_id = NEW.person_id;
    IF can_swim_val IS NULL THEN
        -- Человек не имеет профиля туриста — пропускаем (это инструктор-сторонний и т.п.)
        RETURN NEW;
    END IF;

    IF NOT can_swim_val THEN
        RAISE EXCEPTION
            'Участник % не умеет плавать — нельзя добавить в водный поход %',
            NEW.person_id, NEW.trip_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_water_trip_requires_swim
BEFORE INSERT OR UPDATE ON trip_participant
FOR EACH ROW EXECUTE FUNCTION trg_water_trip_requires_swim();

-- ──────────────────────────────────────────────────────────────────────────
-- 3. Инструктор похода обязан числиться в его участниках.
--    Проверка отложена до COMMIT — иначе порядок INSERT-ов мешает.
-- ──────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_trip_instructor_is_participant()
RETURNS TRIGGER AS $$
DECLARE
    is_member BOOLEAN;
    trip_status TEXT;
BEGIN
    -- Не дёргаем на scheduled — пускай заполняют участников постепенно.
    SELECT status INTO trip_status FROM trip WHERE id = NEW.id;
    IF trip_status = 'scheduled' THEN
        RETURN NEW;
    END IF;
    SELECT EXISTS (
        SELECT 1 FROM trip_participant
        WHERE trip_id = NEW.id AND person_id = NEW.instructor_id
    ) INTO is_member;
    IF NOT is_member THEN
        RAISE EXCEPTION
            'Инструктор % не числится в участниках похода %',
            NEW.instructor_id, NEW.id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER trg_trip_instructor_is_participant
AFTER UPDATE OF status, instructor_id ON trip
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW EXECUTE FUNCTION trg_trip_instructor_is_participant();

-- ──────────────────────────────────────────────────────────────────────────
-- 4. При завершении планового похода — поднять max_passed_difficulty
--    у всех участников-туристов, если новая сложность выше.
-- ──────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION trg_trip_completed_updates_tourist_category()
RETURNS TRIGGER AS $$
DECLARE
    new_sort_order INT;
BEGIN
    IF NEW.kind <> 'planned' OR NEW.status <> 'completed' OR OLD.status = 'completed' THEN
        RETURN NEW;
    END IF;

    SELECT sort_order INTO new_sort_order FROM difficulty WHERE id = NEW.difficulty_id;

    UPDATE tourist t
       SET max_passed_difficulty_id = NEW.difficulty_id
      FROM trip_participant tp
      LEFT JOIN difficulty d_old ON d_old.id = t.max_passed_difficulty_id
     WHERE tp.trip_id = NEW.id
       AND tp.person_id = t.person_id
       AND (t.max_passed_difficulty_id IS NULL OR d_old.sort_order < new_sort_order);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_trip_completed_updates_tourist_category
AFTER UPDATE OF status ON trip
FOR EACH ROW EXECUTE FUNCTION trg_trip_completed_updates_tourist_category();
"""

_DOWNGRADE_SQL = """
DROP TRIGGER IF EXISTS trg_trip_completed_updates_tourist_category ON trip;
DROP FUNCTION IF EXISTS trg_trip_completed_updates_tourist_category();

DROP TRIGGER IF EXISTS trg_trip_instructor_is_participant ON trip;
DROP FUNCTION IF EXISTS trg_trip_instructor_is_participant();

DROP TRIGGER IF EXISTS trg_water_trip_requires_swim ON trip_participant;
DROP FUNCTION IF EXISTS trg_water_trip_requires_swim();

DROP TRIGGER IF EXISTS trg_trip_instructor_qualified ON trip;
DROP FUNCTION IF EXISTS trg_trip_instructor_qualified();
"""


def upgrade() -> None:
    """Поставить триггеры PL/pgSQL."""
    op.execute(_UPGRADE_SQL)


def downgrade() -> None:
    """Снять триггеры и связанные функции."""
    op.execute(_DOWNGRADE_SQL)
