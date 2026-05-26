"""13 :class:`QueryDescriptor`-ов по варианту 4.17."""

from __future__ import annotations

from app.models import Difficulty, Group, Route, Section, Tourist, Trainer
from app.services.queries import RUNNERS
from app.ui.crud.descriptor import FieldKind, FormField
from app.ui.queries.descriptor import QueryDescriptor, ResultColumn

# --- Q1 ---
Q1 = QueryDescriptor(
    key="q1",
    title="1. Туристы клуба",
    description="Список туристов с фильтрами по секции, группе, полу, году рождения и возрасту.",
    params=[
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField("group_id", "Группа", FieldKind.RELATION, required=False, relation_model=Group),
        FormField(
            "sex",
            "Пол",
            FieldKind.CHOICE,
            required=False,
            choices=[("M", "Мужской"), ("F", "Женский")],
        ),
        FormField(
            "birth_year",
            "Год рождения",
            FieldKind.INT,
            required=False,
            min_value=1900,
            max_value=2100,
            default=0,
        ),
        FormField(
            "age", "Возраст", FieldKind.INT, required=False, min_value=0, max_value=150, default=0
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("middle_name", "Отчество"),
        ResultColumn("sex", "Пол", width=60, align="center"),
        ResultColumn("birth_date", "Дата рожд."),
        ResultColumn("category", "Категория", width=110),
        ResultColumn("section", "Секция"),
        ResultColumn("group", "Группа"),
    ],
    runner=RUNNERS["q1"],
)


# --- Q2 ---
Q2 = QueryDescriptor(
    key="q2",
    title="2. Тренеры",
    description="Тренеры с фильтрами по секции, полу, возрасту, зарплате и специализации.",
    params=[
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField(
            "sex",
            "Пол",
            FieldKind.CHOICE,
            required=False,
            choices=[("M", "Мужской"), ("F", "Женский")],
        ),
        FormField(
            "age", "Возраст", FieldKind.INT, required=False, min_value=0, max_value=150, default=0
        ),
        FormField("min_salary", "Зарплата ≥", FieldKind.DECIMAL, required=False, min_value=0),
        FormField("max_salary", "Зарплата ≤", FieldKind.DECIMAL, required=False, min_value=0),
        FormField("specialization", "Специализация (LIKE)", FieldKind.TEXT, required=False),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("sex", "Пол", width=60, align="center"),
        ResultColumn("birth_date", "Дата рожд."),
        ResultColumn("section", "Секция"),
        ResultColumn("specialization", "Специализация"),
        ResultColumn("salary", "Зарплата", align="right"),
        ResultColumn("hire_date", "Приём"),
    ],
    runner=RUNNERS["q2"],
)


# --- Q3 ---
Q3 = QueryDescriptor(
    key="q3",
    title="3. Соревнования спортсменов секции",
    description="Соревнования, в которых участвовали спортсмены/тренеры выбранной секции.",
    params=[
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("name", "Соревнование"),
        ResultColumn("held_at", "Дата"),
        ResultColumn("location", "Место"),
        ResultColumn("discipline", "Дисциплина"),
        ResultColumn("athletes", "Участников", align="right", width=110),
    ],
    runner=RUNNERS["q3"],
)


# --- Q4 ---
Q4 = QueryDescriptor(
    key="q4",
    title="4. Тренеры тренировок в группе за период",
    description="Кто и сколько раз тренировал группу в указанный промежуток дат.",
    params=[
        FormField("group_id", "Группа", FieldKind.RELATION, required=False, relation_model=Group),
        FormField("date_from", "С даты", FieldKind.DATE, required=False),
        FormField("date_to", "По дату", FieldKind.DATE, required=False),
    ],
    result_columns=[
        ResultColumn("id", "ID тренера", width=90, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("sessions_count", "Тренировок", align="right", width=110),
        ResultColumn("first_session", "Первая"),
        ResultColumn("last_session", "Последняя"),
    ],
    runner=RUNNERS["q4"],
)


# --- Q5 ---
Q5 = QueryDescriptor(
    key="q5",
    title="5. Туристы по походам",
    description=(
        "Туристы с фильтрами: секция, группа, точное число походов, конкретный поход, "
        "период, маршрут, точка маршрута, имеющаяся категория."
    ),
    params=[
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField("group_id", "Группа", FieldKind.RELATION, required=False, relation_model=Group),
        FormField(
            "trips_count_eq",
            "Походов = N",
            FieldKind.INT,
            required=False,
            min_value=0,
            max_value=999,
            default=0,
        ),
        FormField(
            "trip_id",
            "ID похода",
            FieldKind.INT,
            required=False,
            min_value=0,
            max_value=10**8,
            default=0,
        ),
        FormField("date_from", "Период с", FieldKind.DATE, required=False),
        FormField("date_to", "Период по", FieldKind.DATE, required=False),
        FormField("route_id", "Маршрут", FieldKind.RELATION, required=False, relation_model=Route),
        FormField("point_name", "Точка маршрута (LIKE)", FieldKind.TEXT, required=False),
        FormField(
            "difficulty_id",
            "Имеет категорию",
            FieldKind.RELATION,
            required=False,
            relation_model=Difficulty,
            relation_label_field="code",
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("trips_count", "Походов", align="right", width=110),
    ],
    runner=RUNNERS["q5"],
)


# --- Q6 ---
Q6 = QueryDescriptor(
    key="q6",
    title="6. Руководители секций",
    description="Руководители секций целиком или с фильтрами по зарплате/году рождения/возрасту/году найма.",
    params=[
        FormField("min_salary", "Зарплата ≥", FieldKind.DECIMAL, required=False, min_value=0),
        FormField("max_salary", "Зарплата ≤", FieldKind.DECIMAL, required=False, min_value=0),
        FormField(
            "birth_year",
            "Год рождения",
            FieldKind.INT,
            required=False,
            min_value=1900,
            max_value=2100,
            default=0,
        ),
        FormField(
            "age", "Возраст", FieldKind.INT, required=False, min_value=0, max_value=150, default=0
        ),
        FormField(
            "hire_year",
            "Год приёма на работу",
            FieldKind.INT,
            required=False,
            min_value=1900,
            max_value=2100,
            default=0,
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("birth_date", "Дата рожд."),
        ResultColumn("salary", "Зарплата", align="right"),
        ResultColumn("hire_date", "Приём"),
    ],
    runner=RUNNERS["q6"],
)


# --- Q7 ---
Q7 = QueryDescriptor(
    key="q7",
    title="7. Нагрузка тренеров",
    description="Нагрузка тренеров по типам занятий (число тренировок и суммарные минуты) за период.",
    params=[
        FormField(
            "trainer_id",
            "Тренер",
            FieldKind.RELATION,
            required=False,
            relation_model=Trainer,
            relation_label_field="person_id",
        ),
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField("date_from", "С даты", FieldKind.DATE, required=False),
        FormField("date_to", "По дату", FieldKind.DATE, required=False),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=80, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("activity_type", "Вид занятий"),
        ResultColumn("sessions_count", "Тренировок", align="right", width=110),
        ResultColumn("total_minutes", "Минут", align="right", width=100),
    ],
    runner=RUNNERS["q7"],
)


# --- Q8 ---
Q8 = QueryDescriptor(
    key="q8",
    title="8. Маршруты по секции/периоду/инструктору/числу групп",
    description="Маршруты с агрегатом по числу пройденных групп (походов).",
    params=[
        FormField(
            "section_id",
            "Секция инструктора",
            FieldKind.RELATION,
            required=False,
            relation_model=Section,
        ),
        FormField(
            "instructor_id",
            "Инструктор",
            FieldKind.RELATION,
            required=False,
            relation_model=Tourist,
            relation_label_field="person_id",
        ),
        FormField("date_from", "Период с", FieldKind.DATE, required=False),
        FormField("date_to", "Период по", FieldKind.DATE, required=False),
        FormField(
            "min_trips",
            "Походов ≥",
            FieldKind.INT,
            required=False,
            min_value=0,
            max_value=10**6,
            default=0,
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("name", "Маршрут"),
        ResultColumn("length_km", "Длина (км)", align="right"),
        ResultColumn("kind", "Тип"),
        ResultColumn("trips_count", "Пройдено раз", align="right", width=120),
    ],
    runner=RUNNERS["q8"],
)


# --- Q9 ---
Q9 = QueryDescriptor(
    key="q9",
    title="9. Маршруты: через точку / длина / категория",
    description="Маршруты по фильтрам: проходят через точку, длиннее N, удовлетворяют категории.",
    params=[
        FormField("point_name", "Точка (LIKE)", FieldKind.TEXT, required=False),
        FormField("min_length_km", "Длина ≥ (км)", FieldKind.DECIMAL, required=False, min_value=0),
        FormField(
            "difficulty_id",
            "Категория сложности",
            FieldKind.RELATION,
            required=False,
            relation_model=Difficulty,
            relation_label_field="code",
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("name", "Маршрут"),
        ResultColumn("length_km", "Длина (км)", align="right"),
        ResultColumn("kind", "Тип"),
    ],
    runner=RUNNERS["q9"],
)


# --- Q10 ---
Q10 = QueryDescriptor(
    key="q10",
    title="10. Туристы для типа похода",
    description="Туристы, способные ходить в указанный тип похода (для water нужен ``can_swim``).",
    params=[
        FormField(
            "kind",
            "Тип похода",
            FieldKind.CHOICE,
            required=False,
            choices=[
                ("hike", "Пеший"),
                ("horse", "Конный"),
                ("water", "Водный"),
                ("mountain", "Горный"),
            ],
        ),
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField("group_id", "Группа", FieldKind.RELATION, required=False, relation_model=Group),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("category", "Категория", width=110),
        ResultColumn(
            "can_swim",
            "Плавает",
            width=90,
            align="center",
            formatter=lambda v: "да" if v else "нет",
        ),
        ResultColumn("section", "Секция"),
    ],
    runner=RUNNERS["q10"],
)


# --- Q11 ---
Q11 = QueryDescriptor(
    key="q11",
    title="11. Инструкторы",
    description="Инструкторы (тренеры/спортсмены) с фильтрами по числу походов, маршруту, точке.",
    params=[
        FormField(
            "category",
            "Категория инструктора",
            FieldKind.CHOICE,
            required=False,
            choices=[("athlete", "Спортсмен"), ("trainer", "Тренер")],
        ),
        FormField("route_id", "Маршрут", FieldKind.RELATION, required=False, relation_model=Route),
        FormField(
            "trip_id",
            "ID конкретного похода",
            FieldKind.INT,
            required=False,
            min_value=0,
            max_value=10**8,
            default=0,
        ),
        FormField("point_name", "Точка маршрута (LIKE)", FieldKind.TEXT, required=False),
        FormField(
            "min_trips",
            "Походов ≥",
            FieldKind.INT,
            required=False,
            min_value=0,
            max_value=10**6,
            default=0,
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("category", "Категория", width=110),
        ResultColumn("led_trips", "Походов", align="right", width=100),
    ],
    runner=RUNNERS["q11"],
)


# --- Q12 ---
Q12 = QueryDescriptor(
    key="q12",
    title="12. Туристы с собственным тренером-инструктором",
    description="Туристы, которые ходили в походы со своим тренером в роли инструктора.",
    params=[
        FormField(
            "section_id", "Секция", FieldKind.RELATION, required=False, relation_model=Section
        ),
        FormField("group_id", "Группа", FieldKind.RELATION, required=False, relation_model=Group),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("section", "Секция"),
        ResultColumn("group", "Группа"),
        ResultColumn("trip_id", "Поход", align="right", width=90),
        ResultColumn("trip_start", "Дата старта"),
    ],
    runner=RUNNERS["q12"],
)


# --- Q13 ---
Q13 = QueryDescriptor(
    key="q13",
    title="13. Туристы по всем (указанным) маршрутам",
    description=(
        "Деление: туристы, прошедшие все маршруты. Можно сузить набор — ID через запятую "
        "(например, ``1,3,7``); пусто — все маршруты в БД."
    ),
    params=[
        FormField(
            "route_ids",
            "ID маршрутов через запятую",
            FieldKind.TEXT,
            required=False,
            placeholder="1,3,7",
        ),
    ],
    result_columns=[
        ResultColumn("id", "ID", width=60, align="right"),
        ResultColumn("last_name", "Фамилия"),
        ResultColumn("first_name", "Имя"),
        ResultColumn("routes_visited", "Уникальных маршрутов", align="right", width=180),
    ],
    runner=RUNNERS["q13"],
)


ALL_QUERIES: list[QueryDescriptor] = [
    Q1,
    Q2,
    Q3,
    Q4,
    Q5,
    Q6,
    Q7,
    Q8,
    Q9,
    Q10,
    Q11,
    Q12,
    Q13,
]
