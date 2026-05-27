"""Описания сущностей для дженерик-CRUD.

Каждая константа — :class:`EntityDescriptor`, который полностью определяет,
как сущность отображается и редактируется. Сущности с композитным PK
(``Attendance``, ``CompetitionParticipation``, ``RolePermission``,
``UserRole``) обрабатываются на уровне родителей и здесь не описаны.
"""

from __future__ import annotations

from app.models import (
    Competition,
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
    TripDiaryEntry,
    TripParticipant,
    TripPlanDay,
)
from app.ui.crud import Column, EntityDescriptor, FieldKind, FormField

# ---- Справочники ----

DIFFICULTY = EntityDescriptor(
    model=Difficulty,
    title="Категории сложности",
    title_singular="Категорию сложности",
    perm_prefix="tourist",  # справочник не требует отдельного права
    default_sort="sort_order",
    search_field="name",
    columns=[
        Column("code", "Код", width=80),
        Column("name", "Название"),
        Column("min_length_km", "Мин. длина (км)", align="right"),
        Column("min_days", "Мин. дней", align="right"),
        Column("sort_order", "Порядок", align="right"),
    ],
    form_fields=[
        FormField("code", "Код", FieldKind.TEXT, max_value=8),
        FormField("name", "Название", FieldKind.TEXT),
        FormField("min_length_km", "Мин. длина (км)", FieldKind.DECIMAL, min_value=0),
        FormField("min_days", "Мин. дней", FieldKind.INT, min_value=1),
        FormField("sort_order", "Порядок сортировки", FieldKind.INT, min_value=1),
    ],
)


ROUTE = EntityDescriptor(
    model=Route,
    title="Маршруты",
    title_singular="Маршрут",
    perm_prefix="route",
    default_sort="name",
    search_field="name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("name", "Название"),
        Column("length_km", "Длина (км)", align="right"),
        Column("kind", "Тип", width=120),
    ],
    form_fields=[
        FormField("name", "Название", FieldKind.TEXT),
        FormField("length_km", "Длина (км)", FieldKind.DECIMAL, min_value=0.01),
        FormField(
            "kind",
            "Тип маршрута",
            FieldKind.CHOICE,
            choices=[
                ("hike", "Пеший"),
                ("horse", "Конный"),
                ("water", "Водный"),
                ("mountain", "Горный"),
            ],
            default="hike",
        ),
    ],
)


ROUTE_POINT = EntityDescriptor(
    model=RoutePoint,
    title="Точки маршрутов",
    title_singular="Точку маршрута",
    perm_prefix="route",
    default_sort="id",
    search_field="name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("route.name", "Маршрут"),
        Column("order_no", "№", width=60, align="right"),
        Column("name", "Название точки"),
    ],
    form_fields=[
        FormField("route", "Маршрут", FieldKind.RELATION, relation_model=Route),
        FormField("order_no", "Порядковый номер", FieldKind.INT, min_value=1),
        FormField("name", "Название точки", FieldKind.TEXT),
    ],
)


COMPETITION = EntityDescriptor(
    model=Competition,
    title="Соревнования",
    title_singular="Соревнование",
    perm_prefix="tourist",
    default_sort="-held_at",
    search_field="name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("name", "Название"),
        Column("held_at", "Дата", width=120),
        Column("location", "Место"),
        Column("discipline", "Дисциплина", width=160),
    ],
    form_fields=[
        FormField("name", "Название", FieldKind.TEXT),
        FormField("held_at", "Дата проведения", FieldKind.DATE),
        FormField("location", "Место проведения", FieldKind.TEXT),
        FormField("discipline", "Дисциплина", FieldKind.TEXT),
    ],
)


# ---- Люди ----

PERSON = EntityDescriptor(
    model=Person,
    title="Физические лица",
    title_singular="Физическое лицо",
    perm_prefix="person",
    default_sort="last_name",
    search_field="last_name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("last_name", "Фамилия"),
        Column("first_name", "Имя"),
        Column("middle_name", "Отчество"),
        Column("sex", "Пол", width=60, align="center"),
        Column("birth_date", "Дата рождения", width=120),
    ],
    form_fields=[
        FormField("last_name", "Фамилия", FieldKind.TEXT, max_value=80),
        FormField("first_name", "Имя", FieldKind.TEXT, max_value=80),
        FormField("middle_name", "Отчество", FieldKind.TEXT, required=False, max_value=80),
        FormField(
            "sex",
            "Пол",
            FieldKind.CHOICE,
            choices=[("M", "Мужской"), ("F", "Женский")],
        ),
        FormField("birth_date", "Дата рождения", FieldKind.DATE),
    ],
)


TOURIST = EntityDescriptor(
    model=Tourist,
    title="Туристы",
    title_singular="Туриста",
    perm_prefix="tourist",
    default_sort="person_id",
    columns=[
        Column("person_id", "ID", width=60, align="right"),
        Column("person.last_name", "Фамилия"),
        Column("person.first_name", "Имя"),
        Column("category", "Категория", width=110),
        Column(
            "can_swim",
            "Плавает",
            width=80,
            align="center",
            formatter=lambda v: "да" if v else "нет",
        ),
        Column("sport_rank", "Разряд", width=120),
        Column("specialization", "Специализация"),
        Column("max_passed_difficulty.code", "Макс. сложн.", width=110, align="center"),
    ],
    form_fields=[
        FormField(
            "person",
            "Физическое лицо",
            FieldKind.RELATION,
            relation_model=Person,
            relation_label_field="last_name",
        ),
        FormField(
            "category",
            "Категория",
            FieldKind.CHOICE,
            choices=[
                ("amateur", "Любитель"),
                ("athlete", "Спортсмен"),
                ("trainer", "Тренер"),
            ],
            default="amateur",
        ),
        FormField("joined_at", "Дата вступления", FieldKind.DATE),
        FormField("can_swim", "Умеет плавать", FieldKind.BOOL, required=False),
        FormField("sport_rank", "Спортивный разряд", FieldKind.TEXT, required=False, max_value=40),
        FormField("specialization", "Специализация", FieldKind.TEXT, required=False, max_value=80),
        FormField(
            "max_passed_difficulty",
            "Макс. пройденная сложность",
            FieldKind.RELATION,
            required=False,
            relation_model=Difficulty,
            relation_label_field="code",
        ),
    ],
)


SECTION_HEAD = EntityDescriptor(
    model=SectionHead,
    title="Руководители секций",
    title_singular="Руководителя секции",
    perm_prefix="section_head",
    default_sort="person_id",
    columns=[
        Column("person_id", "ID", width=60, align="right"),
        Column("person.last_name", "Фамилия"),
        Column("person.first_name", "Имя"),
        Column("salary", "Зарплата", align="right"),
        Column("hire_date", "Дата приёма", width=120),
    ],
    form_fields=[
        FormField(
            "person",
            "Физическое лицо",
            FieldKind.RELATION,
            relation_model=Person,
            relation_label_field="last_name",
        ),
        FormField("salary", "Зарплата", FieldKind.DECIMAL, min_value=0),
        FormField("hire_date", "Дата приёма", FieldKind.DATE),
    ],
)


TRAINER = EntityDescriptor(
    model=Trainer,
    title="Тренеры",
    title_singular="Тренера",
    perm_prefix="trainer",
    default_sort="person_id",
    columns=[
        Column("person_id", "ID", width=60, align="right"),
        Column("person.last_name", "Фамилия"),
        Column("person.first_name", "Имя"),
        Column("section.name", "Секция"),
        Column("specialization", "Специализация"),
        Column("salary", "Зарплата", align="right"),
        Column("hire_date", "Дата приёма", width=120),
    ],
    form_fields=[
        FormField(
            "person",
            "Физическое лицо",
            FieldKind.RELATION,
            relation_model=Person,
            relation_label_field="last_name",
        ),
        FormField("section", "Секция", FieldKind.RELATION, relation_model=Section),
        FormField("specialization", "Специализация", FieldKind.TEXT, max_value=80),
        FormField("salary", "Зарплата", FieldKind.DECIMAL, min_value=0),
        FormField("hire_date", "Дата приёма", FieldKind.DATE),
    ],
)


# ---- Клуб ----

SECTION = EntityDescriptor(
    model=Section,
    title="Секции",
    title_singular="Секцию",
    perm_prefix="section",
    default_sort="name",
    search_field="name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("name", "Название"),
        Column("description", "Описание"),
        Column("head.person.last_name", "Руководитель"),
    ],
    form_fields=[
        FormField("name", "Название", FieldKind.TEXT, max_value=120),
        FormField("description", "Описание", FieldKind.TEXTAREA, required=False, max_value=500),
        FormField(
            "head",
            "Руководитель",
            FieldKind.RELATION,
            relation_model=SectionHead,
            relation_label_field="person_id",
        ),
    ],
)


GROUP = EntityDescriptor(
    model=Group,
    title="Группы",
    title_singular="Группу",
    perm_prefix="group",
    default_sort="name",
    search_field="name",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("section.name", "Секция"),
        Column("name", "Название"),
        Column("trainer.person.last_name", "Тренер"),
    ],
    form_fields=[
        FormField("section", "Секция", FieldKind.RELATION, relation_model=Section),
        FormField(
            "trainer",
            "Тренер",
            FieldKind.RELATION,
            relation_model=Trainer,
            relation_label_field="person_id",
        ),
        FormField("name", "Название группы", FieldKind.TEXT, max_value=120),
    ],
)


GROUP_MEMBERSHIP = EntityDescriptor(
    model=GroupMembership,
    title="Участники групп",
    title_singular="Участника группы",
    perm_prefix="group",
    default_sort="-joined_at",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("group.name", "Группа"),
        Column("tourist.person.last_name", "Турист"),
        Column("joined_at", "Вступил", width=120),
        Column("left_at", "Вышел", width=120),
    ],
    form_fields=[
        FormField("group", "Группа", FieldKind.RELATION, relation_model=Group),
        FormField(
            "tourist",
            "Турист",
            FieldKind.RELATION,
            relation_model=Tourist,
            relation_label_field="person_id",
        ),
        FormField("joined_at", "Дата вступления", FieldKind.DATE),
        FormField("left_at", "Дата выхода (если есть)", FieldKind.DATE, required=False),
    ],
)


# ---- Тренировки ----

TRAINING_SESSION = EntityDescriptor(
    model=TrainingSession,
    title="Тренировки",
    title_singular="Тренировку",
    perm_prefix="training_session",
    default_sort="-scheduled_at",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("group.name", "Группа"),
        Column("trainer.person.last_name", "Тренер"),
        Column("scheduled_at", "Время"),
        Column("duration_min", "Мин.", align="right", width=80),
        Column("activity_type", "Тип занятия"),
        Column("location", "Место"),
    ],
    form_fields=[
        FormField("group", "Группа", FieldKind.RELATION, relation_model=Group),
        FormField(
            "trainer",
            "Тренер",
            FieldKind.RELATION,
            relation_model=Trainer,
            relation_label_field="person_id",
        ),
        FormField("scheduled_at", "Дата (время — 00:00)", FieldKind.DATE),
        FormField("duration_min", "Длительность (минут)", FieldKind.INT, min_value=1, default=60),
        FormField("activity_type", "Тип занятия", FieldKind.TEXT, max_value=80),
        FormField("location", "Место проведения", FieldKind.TEXT, max_value=160),
    ],
)


# ---- Походы ----

TRIP = EntityDescriptor(
    model=Trip,
    title="Походы",
    title_singular="Поход",
    perm_prefix="trip",
    default_sort="-start_date",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("route.name", "Маршрут"),
        Column("difficulty.code", "Сложность", width=110, align="center"),
        Column("kind", "Тип", width=110),
        Column("status", "Статус", width=120),
        Column("start_date", "Старт", width=120),
        Column("days_count", "Дней", align="right", width=80),
        Column("instructor.last_name", "Инструктор"),
    ],
    form_fields=[
        FormField("route", "Маршрут", FieldKind.RELATION, relation_model=Route),
        FormField(
            "instructor",
            "Инструктор",
            FieldKind.RELATION,
            relation_model=Person,
            relation_label_field="last_name",
        ),
        FormField(
            "difficulty",
            "Категория сложности",
            FieldKind.RELATION,
            relation_model=Difficulty,
            relation_label_field="code",
        ),
        FormField("start_date", "Дата начала", FieldKind.DATE),
        FormField("days_count", "Дней", FieldKind.INT, min_value=1, default=3),
        FormField(
            "kind",
            "Тип похода",
            FieldKind.CHOICE,
            choices=[("planned", "Плановый"), ("unplanned", "Неплановый")],
            default="planned",
        ),
        FormField(
            "status",
            "Статус",
            FieldKind.CHOICE,
            choices=[
                ("scheduled", "Запланирован"),
                ("in_progress", "Идёт"),
                ("completed", "Завершён"),
                ("cancelled", "Отменён"),
            ],
            default="scheduled",
        ),
    ],
)


TRIP_PLAN_DAY = EntityDescriptor(
    model=TripPlanDay,
    title="План похода (по дням)",
    title_singular="День плана",
    perm_prefix="trip",
    default_sort="trip_id",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("trip_id", "Поход", width=80, align="right"),
        Column("day_no", "День", width=80, align="right"),
        Column("rest_stops", "Привалы"),
        Column("camp_locations", "Стоянки"),
    ],
    form_fields=[
        FormField(
            "trip", "Поход", FieldKind.RELATION, relation_model=Trip, relation_label_field="id"
        ),
        FormField("day_no", "День", FieldKind.INT, min_value=1, default=1),
        FormField("rest_stops", "Привалы", FieldKind.TEXTAREA, required=False, max_value=500),
        FormField("camp_locations", "Стоянки", FieldKind.TEXTAREA, required=False, max_value=500),
    ],
)


TRIP_DIARY = EntityDescriptor(
    model=TripDiaryEntry,
    title="Дневник похода",
    title_singular="Запись дневника",
    perm_prefix="trip",
    default_sort="-recorded_at",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("trip_id", "Поход", width=80, align="right"),
        Column("day_no", "День", width=80, align="right"),
        Column("recorded_at", "Записано"),
        Column("content", "Текст"),
    ],
    form_fields=[
        FormField(
            "trip", "Поход", FieldKind.RELATION, relation_model=Trip, relation_label_field="id"
        ),
        FormField("day_no", "День", FieldKind.INT, min_value=1, default=1),
        FormField("content", "Содержимое", FieldKind.TEXTAREA),
    ],
)


TRIP_PARTICIPANT = EntityDescriptor(
    model=TripParticipant,
    title="Участники походов",
    title_singular="Участника похода",
    perm_prefix="trip",
    default_sort="trip_id",
    columns=[
        Column("id", "ID", width=60, align="right"),
        Column("trip_id", "Поход", width=80, align="right"),
        Column("person.last_name", "Фамилия"),
        Column("person.first_name", "Имя"),
    ],
    form_fields=[
        FormField(
            "trip", "Поход", FieldKind.RELATION, relation_model=Trip, relation_label_field="id"
        ),
        FormField(
            "person",
            "Участник",
            FieldKind.RELATION,
            relation_model=Person,
            relation_label_field="last_name",
        ),
    ],
)


# ---- Группировка для UI ----

# Все сущности в одном списке, разбитом на смысловые группы. Группа отображается
# в sidebar-е как disabled-заголовок (см. EntityListPage).
DATA_GROUPS: list[tuple[str, list[EntityDescriptor]]] = [
    ("Люди", [PERSON, SECTION_HEAD, TRAINER, TOURIST]),
    ("Структура клуба", [SECTION, GROUP, GROUP_MEMBERSHIP]),
    ("Тренировки и соревнования", [TRAINING_SESSION, COMPETITION]),
    ("Маршруты", [DIFFICULTY, ROUTE, ROUTE_POINT]),
    ("Походы", [TRIP, TRIP_PLAN_DAY, TRIP_DIARY, TRIP_PARTICIPANT]),
]


def all_descriptors() -> list[EntityDescriptor]:
    """Плоский список всех дескрипторов из ``DATA_GROUPS`` (порядок сохраняется)."""
    return [d for _, group in DATA_GROUPS for d in group]
