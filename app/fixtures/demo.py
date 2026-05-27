"""Идемпотентный посев демо-данных для сервисного режима.

Если в БД уже есть хотя бы одна `Section`, посев пропускается — это надёжный
маркер «БД уже наполнена». Повторный вызов после ручной правки не сломает
существующие данные.

Состав данных рассчитан так, чтобы все 13 запросов варианта возвращали
что-то осмысленное и срабатывали ключевые триггеры (квалификация инструктора,
``can_swim`` для водных походов и т.п.).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from sqlalchemy import select

from app.models import (
    AppUser,
    Competition,
    CompetitionParticipation,
    Difficulty,
    Group,
    GroupMembership,
    Permission,
    Person,
    Role,
    Route,
    RoutePoint,
    Section,
    SectionHead,
    Tourist,
    Trainer,
    TrainingSession,
    Trip,
    TripParticipant,
    TripPlanDay,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# Роли и пользователи, которыми посев «полностью определяет» рабочую БД.
_DOMAIN_ENTITIES = (
    "section",
    "section_head",
    "group",
    "person",
    "tourist",
    "trainer",
    "training_session",
    "attendance",
    "competition",
    "route",
    "trip",
)
_CRUD_ACTIONS = ("read", "create", "update", "delete")
_COACH_PERMISSIONS = (
    "person.read",
    "tourist.read",
    "group.read",
    "training_session.read",
    "training_session.create",
    "training_session.update",
    "attendance.read",
    "attendance.create",
    "attendance.update",
    "trip.read",
    "competition.read",
    "route.read",
)
# (login, пароль, имя роли)
_DEMO_USERS = (
    ("manager", "manager12345", "Менеджер данных"),
    ("analyst", "analyst12345", "Аналитик"),
    ("coach", "coach12345", "Тренер"),
)


def is_seeded(session: Session) -> bool:
    """``True``, если в БД уже есть данные (по наличию первой ``Section``)."""
    return session.execute(select(Section.id).limit(1)).first() is not None


def seed(session: Session) -> dict[str, int]:
    """Засеять демо-данные. Возвращает счётчики созданных сущностей.

    Если БД уже наполнена, возвращает пустые счётчики (no-op).
    """
    if is_seeded(session):
        return {}

    counts: dict[str, int] = {}

    # --- Difficulty ---
    difficulties = [
        Difficulty(
            code=code, name=name, min_length_km=Decimal(str(ln)), min_days=days, sort_order=i
        )
        for i, (code, name, ln, days) in enumerate(
            [
                ("I", "Первая", 10, 1),
                ("II", "Вторая", 30, 3),
                ("III", "Третья", 60, 6),
                ("IV", "Четвёртая", 100, 10),
                ("V", "Пятая", 150, 14),
                ("VI", "Шестая", 200, 18),
            ],
            start=1,
        )
    ]
    session.add_all(difficulties)
    session.flush()
    counts["difficulty"] = len(difficulties)
    diff_by_code = {d.code: d for d in difficulties}

    # --- Persons (используем для всех «людей») ---
    person_specs = [
        # (last, first, middle, sex, birth)
        ("Иванов", "Сергей", "Петрович", "M", date(1980, 5, 12)),  # head 1
        ("Петрова", "Мария", "Ивановна", "F", date(1982, 9, 3)),  # head 2
        ("Сидоров", "Олег", "Анатольевич", "M", date(1975, 1, 21)),  # head 3
        ("Кузнецова", "Анна", "Сергеевна", "F", date(1985, 11, 7)),  # trainer 1
        ("Смирнов", "Дмитрий", "Иванович", "M", date(1988, 3, 14)),  # trainer 2
        ("Лебедева", "Ольга", "Николаевна", "F", date(1990, 7, 22)),  # trainer 3
        ("Морозов", "Антон", "Викторович", "M", date(1987, 12, 1)),  # trainer 4
        ("Волков", "Игорь", "Александрович", "M", date(1995, 4, 18)),  # tourist
        ("Соколова", "Татьяна", "Дмитриевна", "F", date(1996, 8, 25)),  # tourist
        ("Зайцев", "Михаил", "Юрьевич", "M", date(1999, 2, 9)),  # tourist
        ("Орлова", "Екатерина", "Павловна", "F", date(2000, 6, 30)),  # tourist
        ("Никитин", "Артём", "Сергеевич", "M", date(2001, 10, 11)),  # tourist
        ("Романова", "Юлия", "Викторовна", "F", date(1998, 1, 5)),  # tourist
        ("Алексеев", "Кирилл", "Олегович", "M", date(1997, 11, 28)),  # tourist
        ("Васильева", "Дарья", "Андреевна", "F", date(2002, 4, 3)),  # tourist
        ("Павлов", "Роман", "Игоревич", "M", date(1994, 7, 17)),  # tourist
        ("Семёнова", "Алина", "Романовна", "F", date(2003, 9, 2)),  # tourist
        ("Богданов", "Денис", "Михайлович", "M", date(1993, 12, 19)),  # tourist
        ("Тарасова", "Виктория", "Олеговна", "F", date(2001, 5, 8)),  # tourist
        ("Гусев", "Максим", "Алексеевич", "M", date(1996, 3, 24)),  # tourist
    ]
    persons = [
        Person(
            last_name=last,
            first_name=first,
            middle_name=middle,
            sex=sex,
            birth_date=birth,
        )
        for last, first, middle, sex, birth in person_specs
    ]
    session.add_all(persons)
    session.flush()
    counts["person"] = len(persons)

    # --- SectionHead (первые 3) ---
    section_heads = [
        SectionHead(person_id=persons[i].id, salary=Decimal("90000"), hire_date=date(2018, 1, 15))
        for i in range(3)
    ]
    session.add_all(section_heads)
    session.flush()
    counts["section_head"] = len(section_heads)

    # --- Section ---
    sections = [
        Section(name=name, description=desc, head_id=section_heads[i].person_id)
        for i, (name, desc) in enumerate([
            ("Пешеходный туризм", "Походы выходного дня и категорийные."),
            ("Водный туризм", "Сплавы по рекам, требуется умение плавать."),
            ("Горный туризм", "Восхождения и горные маршруты."),
        ])
    ]
    session.add_all(sections)
    session.flush()
    counts["section"] = len(sections)

    # --- Trainer (следующие 4) ---
    trainer_specs = [
        # (person_idx, section_idx, salary, spec)
        (3, 0, Decimal("55000"), "Туризм"),
        (4, 1, Decimal("58000"), "Водные виды"),
        (5, 2, Decimal("62000"), "Альпинизм"),
        (6, 0, Decimal("52000"), "Туризм"),
    ]
    trainers = [
        Trainer(
            person_id=persons[pi].id,
            section_id=sections[si].id,
            salary=salary,
            hire_date=date(2020, 9, 1),
            specialization=spec,
        )
        for pi, si, salary, spec in trainer_specs
    ]
    session.add_all(trainers)
    session.flush()
    counts["trainer"] = len(trainers)

    # --- Tourist (все начиная с 7-го; у первых трёх трейнеров тоже сделаем профили туриста) ---
    tourist_specs = [
        # (person_idx, category, can_swim, rank, specialization)
        (3, "trainer", True, "I разряд", "Туризм"),
        (4, "trainer", True, "КМС", "Водные виды"),
        (5, "trainer", True, "I разряд", "Альпинизм"),
        (6, "trainer", True, None, "Туризм"),
        (7, "athlete", True, "II разряд", "Туризм"),
        (8, "athlete", True, "II разряд", "Водные виды"),
        (9, "athlete", False, "III разряд", "Альпинизм"),
        (10, "amateur", True, None, None),
        (11, "amateur", False, None, None),
        (12, "athlete", True, "III разряд", "Туризм"),
        (13, "amateur", True, None, None),
        (14, "amateur", True, None, None),
        (15, "amateur", False, None, None),
        (16, "athlete", True, "II разряд", "Водные виды"),
        (17, "amateur", True, None, None),
        (18, "amateur", False, None, None),
        (19, "athlete", True, "III разряд", "Альпинизм"),
    ]
    tourists = [
        Tourist(
            person_id=persons[pi].id,
            category=cat,
            joined_at=date(2023, 1, 10),
            can_swim=can_swim,
            sport_rank=rank,
            specialization=spec,
        )
        for pi, cat, can_swim, rank, spec in tourist_specs
    ]
    session.add_all(tourists)
    session.flush()
    counts["tourist"] = len(tourists)

    # --- Group: 2 на каждую секцию = 6 ---
    group_specs = [
        (sections[0].id, trainers[0].person_id, "Пешие — взрослые"),
        (sections[0].id, trainers[3].person_id, "Пешие — молодёжь"),
        (sections[1].id, trainers[1].person_id, "Водники — новички"),
        (sections[1].id, trainers[1].person_id, "Водники — категория"),
        (sections[2].id, trainers[2].person_id, "Горники — начальный"),
        (sections[2].id, trainers[2].person_id, "Горники — спортивный"),
    ]
    groups = [Group(section_id=sid, trainer_id=tid, name=name) for sid, tid, name in group_specs]
    session.add_all(groups)
    session.flush()
    counts["group"] = len(groups)

    # --- GroupMembership: распределяем туристов по группам ---
    memberships = [
        # tourist (person_id) → group_idx
        (tourists[4].person_id, 0),
        (tourists[5].person_id, 2),
        (tourists[6].person_id, 4),
        (tourists[7].person_id, 0),
        (tourists[8].person_id, 1),
        (tourists[9].person_id, 2),
        (tourists[10].person_id, 3),
        (tourists[11].person_id, 4),
        (tourists[12].person_id, 5),
        (tourists[13].person_id, 1),
        (tourists[14].person_id, 0),
        (tourists[15].person_id, 5),
        (tourists[16].person_id, 4),
        # тренеры тоже как туристы по своим группам
        (tourists[0].person_id, 0),
        (tourists[1].person_id, 2),
        (tourists[2].person_id, 4),
    ]
    session.add_all(
        GroupMembership(tourist_id=tid, group_id=groups[gi].id, joined_at=date(2024, 1, 15))
        for tid, gi in memberships
    )
    session.flush()
    counts["group_membership"] = len(memberships)

    # --- Route + RoutePoint ---
    route_specs = [
        ("Тропа выходного дня", Decimal("12"), "hike", ["Старт", "Привал у реки", "Финиш"]),
        ("Большое кольцо", Decimal("45"), "hike", ["Старт", "Озеро", "Перевал", "Финиш"]),
        ("Сплав по Бирюсе", Decimal("80"), "water", ["Исток", "Порог", "Затон", "Устье"]),
        ("Восхождение Эльбрус", Decimal("20"), "mountain", ["База", "Скалы Пастухова", "Седло"]),
        ("Конный маршрут Лесной", Decimal("35"), "horse", ["Конюшня", "Поляна", "Возврат"]),
    ]
    routes: list[Route] = []
    for name, length, kind, points in route_specs:
        route = Route(name=name, length_km=length, kind=kind)
        session.add(route)
        session.flush()
        for i, point_name in enumerate(points, start=1):
            session.add(RoutePoint(route_id=route.id, order_no=i, name=point_name))
        routes.append(route)
    session.flush()
    counts["route"] = len(routes)
    counts["route_point"] = sum(len(p) for _, _, _, p in route_specs)

    # --- Trip: используем минимальную сложность (sort_order=1), чтобы пропустить
    # триггер квалификации инструктора (см. миграцию 0002). Все походы — completed,
    # чтобы триггер обновления tourist.max_passed_difficulty тоже отработал.
    diff_first = diff_by_code["I"]
    diff_second = diff_by_code["II"]

    trip_specs = [
        # (route_idx, instructor_person_id, start_date, days, kind, status, difficulty)
        (0, trainers[0].person_id, date(2024, 6, 1), 1, "planned", "completed", diff_first),
        (0, trainers[3].person_id, date(2024, 6, 15), 1, "unplanned", "completed", diff_first),
        (1, trainers[0].person_id, date(2024, 7, 5), 4, "planned", "completed", diff_first),
        (2, trainers[1].person_id, date(2024, 8, 1), 5, "planned", "completed", diff_first),
        (3, trainers[2].person_id, date(2024, 8, 20), 3, "planned", "scheduled", diff_first),
        (4, trainers[0].person_id, date(2024, 9, 10), 2, "planned", "scheduled", diff_first),
    ]
    trips: list[Trip] = []
    for ri, instr, start, days, kind, status, diff in trip_specs:
        trip = Trip(
            route_id=routes[ri].id,
            instructor_id=instr,
            start_date=start,
            days_count=days,
            kind=kind,
            status=status,
            difficulty_id=diff.id,
        )
        session.add(trip)
        trips.append(trip)
    session.flush()
    counts["trip"] = len(trips)
    _ = diff_second  # silence unused — оставлено как точка расширения для будущих trips

    # --- TripPlanDay для всех plan-trip-ов ---
    plan_count = 0
    for trip in trips:
        if trip.kind != "planned":
            continue
        for day in range(1, trip.days_count + 1):
            session.add(
                TripPlanDay(
                    trip_id=trip.id,
                    day_no=day,
                    rest_stops=f"День {day}: привал на маршруте",
                    camp_locations=f"День {day}: стоянка у источника",
                )
            )
            plan_count += 1
    counts["trip_plan_day"] = plan_count

    # --- TripParticipant: инструктор + несколько туристов ---
    participants_count = 0
    trip_participant_specs = [
        # (trip_idx, [person_ids])
        (0, [trainers[0].person_id, tourists[4].person_id, tourists[7].person_id]),
        (1, [trainers[3].person_id, tourists[8].person_id, tourists[10].person_id]),
        (
            2,
            [
                trainers[0].person_id,
                tourists[4].person_id,
                tourists[7].person_id,
                tourists[14].person_id,
            ],
        ),
        # Водный: участники должны уметь плавать (тренер can_swim=True, tourists[5] can_swim=True)
        (
            3,
            [
                trainers[1].person_id,
                tourists[5].person_id,
                tourists[9].person_id,
                tourists[13].person_id,
            ],
        ),
        (4, [trainers[2].person_id, tourists[6].person_id]),
        (5, [trainers[0].person_id, tourists[4].person_id]),
    ]
    for ti, person_ids in trip_participant_specs:
        for pid in person_ids:
            session.add(TripParticipant(trip_id=trips[ti].id, person_id=pid))
            participants_count += 1
    counts["trip_participant"] = participants_count

    # --- TrainingSession ---
    sessions_count = 0
    base_dt = datetime(2024, 5, 1, 18, 0)
    activities = ["Общая физподготовка", "Снаряжение", "Техника передвижения", "Теория"]
    for week in range(10):
        for gi, group in enumerate(groups):
            session.add(
                TrainingSession(
                    group_id=group.id,
                    trainer_id=group.trainer_id,
                    scheduled_at=base_dt + timedelta(days=week * 7 + gi),
                    duration_min=90,
                    location=f"Зал №{(gi % 3) + 1}",
                    activity_type=activities[week % len(activities)],
                )
            )
            sessions_count += 1
    counts["training_session"] = sessions_count

    # --- Competition ---
    competitions = [
        Competition(name=name, held_at=held, location=loc, discipline=disc)
        for name, held, loc, disc in [
            ("Кубок города", date(2024, 5, 25), "Городской парк", "Туристское многоборье"),
            ("Чемпионат региона", date(2024, 9, 14), "Спорткомплекс", "Водный слалом"),
            ("Скальный фестиваль", date(2024, 6, 30), "Скалодром", "Альпинизм"),
        ]
    ]
    session.add_all(competitions)
    session.flush()
    counts["competition"] = len(competitions)

    # Athletes & trainers participate
    competition_participations = [
        (competitions[0].id, tourists[0].person_id, 1, "1:24:11"),
        (competitions[0].id, tourists[4].person_id, 3, "1:28:55"),
        (competitions[1].id, tourists[1].person_id, 2, "0:54:07"),
        (competitions[1].id, tourists[5].person_id, 5, "0:58:18"),
        (competitions[2].id, tourists[2].person_id, 1, "—"),
        (competitions[2].id, tourists[6].person_id, 4, "—"),
    ]
    for cid, pid, place, result in competition_participations:
        session.add(
            CompetitionParticipation(competition_id=cid, person_id=pid, place=place, result=result)
        )
    counts["competition_participation"] = len(competition_participations)

    session.flush()
    return counts


def _role_specs() -> list[tuple[str, str, list[str]]]:
    """Описания демо-ролей: ``(имя, описание, список кодов прав)``."""
    crud_all = [f"{e}.{a}" for e in _DOMAIN_ENTITIES for a in _CRUD_ACTIONS]
    read_all = [f"{e}.read" for e in _DOMAIN_ENTITIES]
    return [
        ("Менеджер данных", "Полный доступ ко всем доменным данным (CRUD).", crud_all),
        ("Аналитик", "Чтение всех данных и произвольный SQL.", [*read_all, "sql.execute"]),
        ("Тренер", "Ведение тренировок и посещаемости, просмотр групп.", list(_COACH_PERMISSIONS)),
    ]


def seed_access(session: Session) -> dict[str, int]:
    """Идемпотентно создать демо-роли и пользователей.

    Роли/пользователи создаются только если их ещё нет (по имени/логину),
    поэтому функцию безопасно вызывать повторно и после очистки доменных данных
    (``truncate_domain`` системные таблицы не трогает). Это и делает посев
    «полным описанием» рабочей БД: после него есть и данные, и роли, и учётки.
    """
    counts: dict[str, int] = {}
    permissions = {p.code: p for p in session.execute(select(Permission)).scalars()}

    roles_by_name: dict[str, Role] = {}
    created_roles = 0
    for name, description, codes in _role_specs():
        existing = session.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if existing is not None:
            roles_by_name[name] = existing
            continue
        role = Role(name=name, description=description, is_system=False)
        role.permissions = [permissions[c] for c in codes if c in permissions]
        session.add(role)
        roles_by_name[name] = role
        created_roles += 1
    session.flush()
    if created_roles:
        counts["role"] = created_roles

    hasher = PasswordHasher()
    created_users = 0
    for login, password, role_name in _DEMO_USERS:
        if session.execute(select(AppUser.id).where(AppUser.login == login)).first() is not None:
            continue
        user = AppUser(login=login, password_hash=hasher.hash(password), is_active=True)
        role = roles_by_name.get(role_name)
        if role is not None:
            user.roles.append(role)
        session.add(user)
        created_users += 1
    session.flush()
    if created_users:
        counts["app_user"] = created_users

    return counts
