"""13 runner-функций для запросов варианта 4.17.

Каждая функция принимает открытую SQLAlchemy-сессию и словарь параметров
из UI; возвращает список словарей-строк, готовых для ``ResultTableModel``.
Параметры опциональны: пустые значения отбрасываются ``QueryView`` ещё до
вызова, так что внутри сразу проверяем ``params.get(...)`` и сужаем выборку.

Запросы рассчитаны на PostgreSQL — используют ``extract()`` и ``date()``
из стандартного SQL, без диалектных конструкций сверх этого.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Integer,
    Select,
    and_,
    cast,
    distinct,
    extract,
    func,
    not_,
    select,
)

from app.models import (
    Competition,
    CompetitionParticipation,
    Difficulty,
    Group,
    GroupMembership,
    Person,
    Route,
    RoutePoint,
    Section,
    SectionHead,
    Tourist,
    Trainer,
    TrainingSession,
    Trip,
    TripParticipant,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _rows(session: Session, stmt: Select) -> list[dict[str, Any]]:
    return [dict(row) for row in session.execute(stmt).mappings().all()]


def _age_expr(birth: Any) -> Any:
    """Кросс-диалектный возраст: целое число полных лет от ``birth`` до сегодня."""
    today = date.today()
    return cast(
        extract("year", birth) * 0 + (today.year - extract("year", birth)),
        Integer,
    )


# --- Q1 ---
def q1_tourists(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Туристы: фильтры по секции/группе/полу/году рождения/возрасту."""
    stmt = (
        select(
            Tourist.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Person.middle_name.label("middle_name"),
            Person.sex.label("sex"),
            Person.birth_date.label("birth_date"),
            Section.name.label("section"),
            Group.name.label("group"),
            Tourist.category.label("category"),
        )
        .select_from(Tourist)
        .join(Person, Person.id == Tourist.person_id)
        .outerjoin(
            GroupMembership,
            and_(
                GroupMembership.tourist_id == Tourist.person_id,
                GroupMembership.left_at.is_(None),
            ),
        )
        .outerjoin(Group, Group.id == GroupMembership.group_id)
        .outerjoin(Section, Section.id == Group.section_id)
        .order_by(Person.last_name, Person.first_name)
    )
    if p.get("section_id"):
        stmt = stmt.where(Section.id == p["section_id"])
    if p.get("group_id"):
        stmt = stmt.where(Group.id == p["group_id"])
    if p.get("sex"):
        stmt = stmt.where(Person.sex == p["sex"])
    if p.get("birth_year"):
        stmt = stmt.where(extract("year", Person.birth_date) == p["birth_year"])
    if p.get("age"):
        target_year = date.today().year - int(p["age"])
        stmt = stmt.where(extract("year", Person.birth_date) == target_year)
    return _rows(session, stmt)


# --- Q2 ---
def q2_trainers(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Тренеры: фильтры по секции/полу/возрасту/зарплате/специализации."""
    stmt = (
        select(
            Trainer.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Person.sex.label("sex"),
            Person.birth_date.label("birth_date"),
            Section.name.label("section"),
            Trainer.specialization.label("specialization"),
            Trainer.salary.label("salary"),
            Trainer.hire_date.label("hire_date"),
        )
        .join(Person, Person.id == Trainer.person_id)
        .join(Section, Section.id == Trainer.section_id)
        .order_by(Person.last_name, Person.first_name)
    )
    if p.get("section_id"):
        stmt = stmt.where(Trainer.section_id == p["section_id"])
    if p.get("sex"):
        stmt = stmt.where(Person.sex == p["sex"])
    if p.get("age"):
        target_year = date.today().year - int(p["age"])
        stmt = stmt.where(extract("year", Person.birth_date) == target_year)
    if p.get("min_salary") is not None:
        stmt = stmt.where(Trainer.salary >= p["min_salary"])
    if p.get("max_salary") is not None:
        stmt = stmt.where(Trainer.salary <= p["max_salary"])
    if p.get("specialization"):
        stmt = stmt.where(Trainer.specialization.ilike(f"%{p['specialization']}%"))
    return _rows(session, stmt)


# --- Q3 ---
def q3_competitions_of_section_athletes(
    session: Session, p: dict[str, Any]
) -> list[dict[str, Any]]:
    """Соревнования, в которых участвовали спортсмены указанной секции."""
    stmt = (
        select(
            Competition.id.label("id"),
            Competition.name.label("name"),
            Competition.held_at.label("held_at"),
            Competition.location.label("location"),
            Competition.discipline.label("discipline"),
            func.count(distinct(CompetitionParticipation.person_id)).label("athletes"),
        )
        .select_from(Competition)
        .join(CompetitionParticipation, CompetitionParticipation.competition_id == Competition.id)
        .join(Person, Person.id == CompetitionParticipation.person_id)
        .join(Tourist, Tourist.person_id == Person.id)
        .where(Tourist.category.in_(("athlete", "trainer")))
        .group_by(
            Competition.id,
            Competition.name,
            Competition.held_at,
            Competition.location,
            Competition.discipline,
        )
        .order_by(Competition.held_at.desc())
    )
    if p.get("section_id"):
        stmt = stmt.join(
            GroupMembership,
            and_(
                GroupMembership.tourist_id == Tourist.person_id,
                GroupMembership.left_at.is_(None),
            ),
        ).join(
            Group, and_(Group.id == GroupMembership.group_id, Group.section_id == p["section_id"])
        )
    return _rows(session, stmt)


# --- Q4 ---
def q4_trainers_of_group_in_period(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Тренеры, проводившие тренировки в группе за период."""
    stmt = (
        select(
            Trainer.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            func.count(TrainingSession.id).label("sessions_count"),
            func.min(TrainingSession.scheduled_at).label("first_session"),
            func.max(TrainingSession.scheduled_at).label("last_session"),
        )
        .select_from(TrainingSession)
        .join(Trainer, Trainer.person_id == TrainingSession.trainer_id)
        .join(Person, Person.id == Trainer.person_id)
        .group_by(Trainer.person_id, Person.last_name, Person.first_name)
        .order_by(Person.last_name)
    )
    if p.get("group_id"):
        stmt = stmt.where(TrainingSession.group_id == p["group_id"])
    if p.get("date_from"):
        stmt = stmt.where(TrainingSession.scheduled_at >= p["date_from"])
    if p.get("date_to"):
        stmt = stmt.where(TrainingSession.scheduled_at <= p["date_to"])
    return _rows(session, stmt)


# --- Q5 ---
def q5_tourists_by_trips(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Туристы по различным «походным» критериям (агрегатные фильтры)."""
    base = (
        select(
            Tourist.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            func.count(distinct(TripParticipant.trip_id)).label("trips_count"),
        )
        .select_from(Tourist)
        .join(Person, Person.id == Tourist.person_id)
        .outerjoin(TripParticipant, TripParticipant.person_id == Tourist.person_id)
        .outerjoin(Trip, Trip.id == TripParticipant.trip_id)
        .group_by(Tourist.person_id, Person.last_name, Person.first_name)
        .order_by(Person.last_name)
    )
    if p.get("section_id") or p.get("group_id"):
        base = base.join(
            GroupMembership,
            and_(
                GroupMembership.tourist_id == Tourist.person_id,
                GroupMembership.left_at.is_(None),
            ),
        )
        if p.get("group_id"):
            base = base.where(GroupMembership.group_id == p["group_id"])
        if p.get("section_id"):
            base = base.join(
                Group,
                and_(Group.id == GroupMembership.group_id, Group.section_id == p["section_id"]),
            )
    if p.get("trip_id"):
        base = base.where(TripParticipant.trip_id == p["trip_id"])
    if p.get("date_from"):
        base = base.where(Trip.start_date >= p["date_from"])
    if p.get("date_to"):
        base = base.where(Trip.start_date <= p["date_to"])
    if p.get("route_id"):
        base = base.where(Trip.route_id == p["route_id"])
    if p.get("point_name"):
        base = base.join(RoutePoint, RoutePoint.route_id == Trip.route_id).where(
            RoutePoint.name.ilike(f"%{p['point_name']}%")
        )
    if p.get("difficulty_id"):
        base = base.where(Tourist.max_passed_difficulty_id == p["difficulty_id"])
    if p.get("trips_count_eq") is not None:
        base = base.having(func.count(distinct(TripParticipant.trip_id)) == p["trips_count_eq"])
    return _rows(session, base)


# --- Q6 ---
def q6_section_heads(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Руководители секций с фильтрами по зарплате/году рождения/возрасту/году найма."""
    stmt = (
        select(
            SectionHead.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Person.birth_date.label("birth_date"),
            SectionHead.salary.label("salary"),
            SectionHead.hire_date.label("hire_date"),
        )
        .join(Person, Person.id == SectionHead.person_id)
        .order_by(Person.last_name)
    )
    if p.get("min_salary") is not None:
        stmt = stmt.where(SectionHead.salary >= p["min_salary"])
    if p.get("max_salary") is not None:
        stmt = stmt.where(SectionHead.salary <= p["max_salary"])
    if p.get("birth_year"):
        stmt = stmt.where(extract("year", Person.birth_date) == p["birth_year"])
    if p.get("age"):
        target_year = date.today().year - int(p["age"])
        stmt = stmt.where(extract("year", Person.birth_date) == target_year)
    if p.get("hire_year"):
        stmt = stmt.where(extract("year", SectionHead.hire_date) == p["hire_year"])
    return _rows(session, stmt)


# --- Q7 ---
def q7_trainer_workload(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Нагрузка тренеров (минуты по типам занятий за период)."""
    stmt = (
        select(
            Trainer.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            TrainingSession.activity_type.label("activity_type"),
            func.count(TrainingSession.id).label("sessions_count"),
            func.sum(TrainingSession.duration_min).label("total_minutes"),
        )
        .select_from(TrainingSession)
        .join(Trainer, Trainer.person_id == TrainingSession.trainer_id)
        .join(Person, Person.id == Trainer.person_id)
        .group_by(
            Trainer.person_id,
            Person.last_name,
            Person.first_name,
            TrainingSession.activity_type,
        )
        .order_by(Person.last_name, TrainingSession.activity_type)
    )
    if p.get("trainer_id"):
        stmt = stmt.where(Trainer.person_id == p["trainer_id"])
    if p.get("section_id"):
        stmt = stmt.where(Trainer.section_id == p["section_id"])
    if p.get("date_from"):
        stmt = stmt.where(TrainingSession.scheduled_at >= p["date_from"])
    if p.get("date_to"):
        stmt = stmt.where(TrainingSession.scheduled_at <= p["date_to"])
    return _rows(session, stmt)


# --- Q8 ---
def q8_routes_by_section(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Маршруты с фильтрами по секции/периоду/инструктору/числу групп."""
    stmt = (
        select(
            Route.id.label("id"),
            Route.name.label("name"),
            Route.length_km.label("length_km"),
            Route.kind.label("kind"),
            func.count(distinct(Trip.id)).label("trips_count"),
        )
        .select_from(Route)
        .outerjoin(Trip, Trip.route_id == Route.id)
        .group_by(Route.id, Route.name, Route.length_km, Route.kind)
        .order_by(Route.name)
    )
    if p.get("instructor_id"):
        stmt = stmt.where(Trip.instructor_id == p["instructor_id"])
    if p.get("date_from"):
        stmt = stmt.where(Trip.start_date >= p["date_from"])
    if p.get("date_to"):
        stmt = stmt.where(Trip.start_date <= p["date_to"])
    if p.get("section_id"):
        # «секция» маршрута — через тренера-инструктора похода
        stmt = stmt.join(Trainer, Trainer.person_id == Trip.instructor_id).where(
            Trainer.section_id == p["section_id"]
        )
    if p.get("min_trips") is not None:
        stmt = stmt.having(func.count(distinct(Trip.id)) >= p["min_trips"])
    return _rows(session, stmt)


# --- Q9 ---
def q9_routes_through_point(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Маршруты: через точку / длиннее N / удовлетворяют категории."""
    stmt = (
        select(
            Route.id.label("id"),
            Route.name.label("name"),
            Route.length_km.label("length_km"),
            Route.kind.label("kind"),
        )
        .select_from(Route)
        .order_by(Route.name)
        .distinct()
    )
    if p.get("point_name"):
        stmt = stmt.join(RoutePoint, RoutePoint.route_id == Route.id).where(
            RoutePoint.name.ilike(f"%{p['point_name']}%")
        )
    if p.get("min_length_km") is not None:
        stmt = stmt.where(Route.length_km >= p["min_length_km"])
    if p.get("difficulty_id"):
        diff = session.get(Difficulty, p["difficulty_id"])
        if diff is not None:
            stmt = stmt.where(
                and_(
                    Route.length_km >= diff.min_length_km,
                )
            )
    return _rows(session, stmt)


# --- Q10 ---
def q10_tourists_for_trip_kind(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Туристы, способные ходить в заданный тип похода (учёт ``can_swim``)."""
    stmt = (
        select(
            Tourist.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Tourist.can_swim.label("can_swim"),
            Tourist.category.label("category"),
            Section.name.label("section"),
        )
        .select_from(Tourist)
        .join(Person, Person.id == Tourist.person_id)
        .outerjoin(
            GroupMembership,
            and_(
                GroupMembership.tourist_id == Tourist.person_id,
                GroupMembership.left_at.is_(None),
            ),
        )
        .outerjoin(Group, Group.id == GroupMembership.group_id)
        .outerjoin(Section, Section.id == Group.section_id)
        .order_by(Person.last_name)
    )
    kind = p.get("kind")
    if kind == "water":
        stmt = stmt.where(Tourist.can_swim.is_(True))
    if p.get("section_id"):
        stmt = stmt.where(Section.id == p["section_id"])
    if p.get("group_id"):
        stmt = stmt.where(Group.id == p["group_id"])
    return _rows(session, stmt)


# --- Q11 ---
def q11_instructors(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Инструкторы: по категории / числу походов / маршруту / точке."""
    stmt = (
        select(
            Person.id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Tourist.category.label("category"),
            func.count(distinct(Trip.id)).label("led_trips"),
        )
        .select_from(Trip)
        .join(Person, Person.id == Trip.instructor_id)
        .outerjoin(Tourist, Tourist.person_id == Person.id)
        .group_by(Person.id, Person.last_name, Person.first_name, Tourist.category)
        .order_by(Person.last_name)
    )
    cat = p.get("category")
    if cat == "athlete":
        stmt = stmt.where(Tourist.category == "athlete")
    elif cat == "trainer":
        stmt = stmt.where(Tourist.category == "trainer")
    if p.get("route_id"):
        stmt = stmt.where(Trip.route_id == p["route_id"])
    if p.get("trip_id"):
        stmt = stmt.where(Trip.id == p["trip_id"])
    if p.get("point_name"):
        stmt = stmt.join(RoutePoint, RoutePoint.route_id == Trip.route_id).where(
            RoutePoint.name.ilike(f"%{p['point_name']}%")
        )
    if p.get("min_trips") is not None:
        stmt = stmt.having(func.count(distinct(Trip.id)) >= p["min_trips"])
    return _rows(session, stmt)


# --- Q12 ---
def q12_tourists_with_own_trainer_as_instructor(
    session: Session, p: dict[str, Any]
) -> list[dict[str, Any]]:
    """Туристы, ходившие в поход со своим тренером (тот был инструктором похода)."""
    stmt = (
        select(
            Tourist.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            Group.name.label("group"),
            Section.name.label("section"),
            Trip.id.label("trip_id"),
            Trip.start_date.label("trip_start"),
        )
        .select_from(Tourist)
        .join(Person, Person.id == Tourist.person_id)
        .join(GroupMembership, GroupMembership.tourist_id == Tourist.person_id)
        .join(Group, Group.id == GroupMembership.group_id)
        .join(Section, Section.id == Group.section_id)
        .join(TripParticipant, TripParticipant.person_id == Tourist.person_id)
        .join(
            Trip, and_(Trip.id == TripParticipant.trip_id, Trip.instructor_id == Group.trainer_id)
        )
        .order_by(Person.last_name, Trip.start_date.desc())
        .distinct()
    )
    if p.get("section_id"):
        stmt = stmt.where(Section.id == p["section_id"])
    if p.get("group_id"):
        stmt = stmt.where(Group.id == p["group_id"])
    return _rows(session, stmt)


# --- Q13 ---
def q13_tourists_visited_all_routes(session: Session, p: dict[str, Any]) -> list[dict[str, Any]]:
    """Туристы, которые ходили по всем маршрутам (или по всем указанным).

    Параметр ``route_ids`` — строка ID через запятую (``"1,3,7"``). Пусто — берутся
    все маршруты в БД.
    """
    if p.get("route_ids"):
        raw = str(p["route_ids"])
        try:
            target_ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        except ValueError:
            target_ids = []
    else:
        target_ids = [r[0] for r in session.execute(select(Route.id)).all()]

    if not target_ids:
        return []

    # NOT EXISTS (target route WHERE NOT EXISTS (trip_participant for this tourist on that route))
    target_route = Route.__table__.alias("target_route")
    missing_route = (
        select(target_route.c.id)
        .where(target_route.c.id.in_(target_ids))
        .where(
            not_(
                select(TripParticipant.id)
                .join(Trip, Trip.id == TripParticipant.trip_id)
                .where(TripParticipant.person_id == Tourist.person_id)
                .where(Trip.route_id == target_route.c.id)
                .exists()
            )
        )
    )

    stmt = (
        select(
            Tourist.person_id.label("id"),
            Person.last_name.label("last_name"),
            Person.first_name.label("first_name"),
            cast(func.count(distinct(Trip.route_id)), Integer).label("routes_visited"),
        )
        .select_from(Tourist)
        .join(Person, Person.id == Tourist.person_id)
        .outerjoin(TripParticipant, TripParticipant.person_id == Tourist.person_id)
        .outerjoin(Trip, Trip.id == TripParticipant.trip_id)
        .where(not_(missing_route.exists()))
        .group_by(Tourist.person_id, Person.last_name, Person.first_name)
        .order_by(Person.last_name)
    )
    return _rows(session, stmt)


# --- Удобный реестр для регистрации в дескрипторах ---
RUNNERS = {
    "q1": q1_tourists,
    "q2": q2_trainers,
    "q3": q3_competitions_of_section_athletes,
    "q4": q4_trainers_of_group_in_period,
    "q5": q5_tourists_by_trips,
    "q6": q6_section_heads,
    "q7": q7_trainer_workload,
    "q8": q8_routes_by_section,
    "q9": q9_routes_through_point,
    "q10": q10_tourists_for_trip_kind,
    "q11": q11_instructors,
    "q12": q12_tourists_with_own_trainer_as_instructor,
    "q13": q13_tourists_visited_all_routes,
}


# Утилитарные импорты для тестов
__all__ = [
    "RUNNERS",
    "q1_tourists",
    "q2_trainers",
    "q3_competitions_of_section_athletes",
    "q4_trainers_of_group_in_period",
    "q5_tourists_by_trips",
    "q6_section_heads",
    "q7_trainer_workload",
    "q8_routes_by_section",
    "q9_routes_through_point",
    "q10_tourists_for_trip_kind",
    "q11_instructors",
    "q12_tourists_with_own_trainer_as_instructor",
    "q13_tourists_visited_all_routes",
]
