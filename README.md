# Tourist Club — ИС туристического клуба

Итоговый проект по курсу «Базы данных», вариант 4.17. Десктопное приложение на
PySide6 поверх PostgreSQL с полноценным CRUD, 13 параметризованными запросами по
варианту, SQL-консолью, ролевой моделью (ACL) и сервисным режимом.

| Стек          | Решение                                          |
|---------------|--------------------------------------------------|
| Язык          | Python 3.12+                                     |
| UI            | PySide6 (Qt 6), кастомные QSS-темы               |
| ORM           | SQLAlchemy 2.0 (typed declarative)               |
| Миграции      | Alembic                                          |
| СУБД          | PostgreSQL 16 (в Docker)                         |
| Просмотр БД   | Adminer (http://localhost:8080)                  |
| Конфиг        | pydantic-settings + `.env`                       |
| Пароли        | argon2-cffi                                      |
| Менеджер пак. | uv                                               |
| Качество      | Ruff (lint + format), pytest (+ pytest-qt)       |

## Документация

- [docs/specification.md](docs/specification.md) — контракт реализации.
- [docs/plan.md](docs/plan.md) — план работ по этапам (выполнен).
- [docs/er-diagram.md](docs/er-diagram.md) — финальная схема БД (Mermaid + таблица сущностей).
- [docs/screens.md](docs/screens.md) — карта экранов и пользовательские потоки.
- [docs/task.md](docs/task.md), [docs/requirements.md](docs/requirements.md) — исходное ТЗ.

## Быстрый старт

Требуется: **Python 3.12+**, [**uv**](https://docs.astral.sh/uv/), **Docker** + Docker Compose.

```bash
git clone <repo>
cd papuan-database

# 1) Конфиг
cp .env.example .env
#    Отредактируйте пароли в .env ДО первого `docker compose up`,
#    иначе они вшиваются в volume Postgres-а.

# 2) Поднимаем БД
docker compose up -d
#    → Postgres на 5432, Adminer на http://localhost:8080

# 3) Зависимости приложения
uv sync

# 4) Миграции (схема + триггеры + admin + read-only роль)
uv run alembic upgrade head

# 5) Проверка подключения
uv run python -m app.cli check-db --readonly

# 6) Запуск GUI
uv run python -m app
```

В окне логина введите учётку, которую заложила миграция 0003:

| Поле   | Значение                                          |
|--------|---------------------------------------------------|
| Логин  | `admin`                                           |
| Пароль | значение `APP_DEFAULT_ADMIN_PASSWORD` из `.env` (по умолчанию `admin`) |

После первого входа сразу зайдите в **«Сервисный режим» → «Засеять демо-данные»** —
все 16 справочников и 13 запросов сразу наполнятся осмысленным содержимым.

## Архитектура

Слои сверху вниз:

```
app/ui/           PySide6 виджеты, окна, темы
app/viewmodels/   состояние экранов (зарезервировано под будущие)
app/services/     бизнес-логика, ACL, транзакции
app/repositories/ доступ к данным (SQLAlchemy)
app/models/       ORM-модели (26 классов)
app/db/           engine, session-factory, миграции
app/core/         конфиг, логирование, ошибки, события, история SQL
app/fixtures/     демо-данные для сервисного режима
```

Подробнее — `docs/specification.md` §6.1, соглашения по UI — §5.6.

## Роли и права по умолчанию

Миграция `0003_seed_permissions_and_admin` создаёт:

- **44+5 прав** — для каждой из 11 доменных групп сущностей (`tourist.read`,
  `tourist.create`, `tourist.update`, `tourist.delete`, аналогично `section`,
  `group`, `person`, `trainer`, `section_head`, `training_session`, `attendance`,
  `competition`, `route`, `trip`), плюс системные: `admin.users`, `admin.roles`,
  `sql.execute`, `sql.execute_write`, `service.testdata`.
- **Роль `superadmin`** (`is_system=True`, нередактируемая) со всеми правами.
- **Пользователь `admin`** с этой ролью; пароль — из `.env`.

Создавать новые роли с произвольным набором прав можно в
**«Администрирование → Роли»**: чекбокс-матрица прав, сгруппированных по сущностям.
Пользовательские роли можно переименовывать, удалять и менять им набор прав;
системную `superadmin` редактировать нельзя.

## Миграции

```bash
uv run alembic current        # текущая ревизия
uv run alembic history        # история
uv run alembic upgrade head   # накатить всё
uv run alembic downgrade -1   # откатить одну ступень
```

Состав миграций:

| ID   | Что делает                                                                |
|------|---------------------------------------------------------------------------|
| 0001 | 26 таблиц с PK/FK/UNIQUE/CHECK + партиальный индекс активного членства    |
| 0002 | 4 триггера PL/pgSQL (см. ниже)                                            |
| 0003 | Справочник прав, роль `superadmin`, пользователь `admin`                  |
| 0004 | Postgres-роль `tourist_ro` с `SELECT`-only для SQL-консоли                |

Триггеры в `0002`:

1. **`trg_trip_instructor_qualified`** — инструктор должен раньше пройти поход
   сложности ≥ текущей (пропуск для самой низкой категории).
2. **`trg_water_trip_requires_swim`** — на водный маршрут не добавишь туриста
   с `can_swim=False`.
3. **`trg_trip_instructor_is_participant`** (`DEFERRABLE INITIALLY DEFERRED`) —
   инструктор должен числиться в участниках своего похода.
4. **`trg_trip_completed_updates_tourist_category`** — при `status → completed`
   у участников-туристов поднимается `max_passed_difficulty_id`.

## Сервисный режим

В разделе **«Сервисный режим»** (видит только пользователь с правом
`service.testdata`) три кнопки:

- **Очистить БД** — `DELETE` доменных таблиц (системные — `app_user`, `role`,
  `permission`, ассоциации, `audit_login` — не трогаются). Двойное подтверждение.
- **Засеять демо-данными** — идемпотентный посев (6 категорий сложности,
  3 секции, 6 групп, 17 туристов, 4 тренера, 5 маршрутов, 6 походов,
  60 тренировок, 3 соревнования). Повторный вызов пропускается.
- **Экспортировать дамп** — через `pg_dump` (требует наличия в PATH).

## SQL-консоль

Раздел **«SQL-консоль»** (требует право `sql.execute`):

- **Read-only режим (по умолчанию)** — подключение под Postgres-ролью `tourist_ro`,
  `INSERT`/`UPDATE` блокируется самим Postgres. После каждого выполнения —
  автоматический `ROLLBACK`.
- **Full режим** — подключение под основным пользователем БД. После выполнения
  транзакция **остаётся открытой**; нужно явно нажать `Применить (COMMIT)` или
  `Откатить (ROLLBACK)`. Новый `Выполнить` автоматически откатывает предыдущее.
- **История** — последние 50 запросов сохраняются в JSON в
  `platformdirs.user_data_dir`, доступны через выпадающий список.
- **Экспорт результата в CSV** — для SELECT-ов.

Горячие клавиши: `Ctrl+Enter` / `Ctrl+Return` — выполнить.

## Темы

Light и Dark переключаются без перезапуска (кнопка «Тема» внизу sidebar-а).
Все цвета — в `app/theme/tokens.py` (одна дата-классa на тему); QSS
собирается шаблоном в `app/theme/qss.py`. Никаких инлайн-стилей в виджетах.

## Качество кода

```bash
uv run ruff check .            # линт
uv run ruff format --check .   # проверка форматирования
uv run ruff format .           # авто-исправить
uv run pytest                  # тесты (110 шт, ~5 с)
```

Mypy строгий (`strict = true`) запускается отдельно:

```bash
uv run mypy app
```

Конвенции описаны в `docs/specification.md` §6.3 (кодстайл) и §5.6 (UI).

## Структура проекта

```
papuan-database/
├── app/
│   ├── core/         # config, logging, errors, events, query_history
│   ├── db/           # engine, session
│   ├── models/       # 26 ORM-классов (people/club/training/competitions/trips/security)
│   ├── repositories/ # дженерик Repository[T]
│   ├── services/     # auth, acl, users, roles, audit, entity_service, sql_console,
│   │                 # maintenance, queries (13 раннеров)
│   ├── ui/
│   │   ├── crud/         # CrudView, FormDialog, TableModel, form_builder
│   │   ├── queries/      # QueryView, ResultTableModel, 13 дескрипторов, csv_export
│   │   ├── admin/        # UsersPanel, RolesPanel, AuditPanel, dialogs
│   │   ├── descriptors.py, pages.py, sql_console.py, service_panel.py,
│   │   ├── login_window.py, main_window.py, app_controller.py, widgets.py
│   ├── theme/        # tokens (light/dark), qss-шаблон, apply_theme
│   ├── fixtures/     # demo-data seed
│   ├── cli.py        # `python -m app.cli check-db [--readonly]`
│   └── __main__.py   # точка входа GUI
├── migrations/       # Alembic env + 4 миграции
├── tests/            # 110 тестов: repository, services, queries, UI smoke, maintenance
├── docs/
├── docker-compose.yml
├── .env.example
├── alembic.ini
├── pyproject.toml, ruff.toml, mypy.ini
└── README.md
```

## Частые проблемы (FAQ)

**`alembic upgrade head` падает на `CREATE ROLE`.**
Имя/пароль read-only пользователя берётся из `.env`. Проверьте, что
`DB_READONLY_USER` — валидный SQL-идентификатор (только буквы/цифры/`_`).

**Контейнер Postgres «не принимает» новый пароль.**
Пароль вшивается в volume при **первом** старте. Чтобы сменить — либо
`ALTER USER` в psql, либо `docker compose down -v` (удалит данные) и поднять заново.

**В Adminer не виден read-only пользователь.**
`tourist_ro` создаётся миграцией `0004`. Если миграция упала на полпути,
её можно перенакатить: `alembic downgrade 0003 && alembic upgrade head`.

**Экспорт дампа в сервисном режиме выдаёт «pg_dump не найден».**
Установите PostgreSQL client tools и добавьте в PATH:
- Windows: `winget install PostgreSQL.PostgreSQL`, перезапустить терминал.
- macOS: `brew install libpq && brew link --force libpq`.
- Linux: `apt install postgresql-client`.

**Запрос #13 («туристы по всем маршрутам») возвращает пусто.**
Это деление: турист должен **уже** пройти все указанные маршруты. На свежей
демо-базе таких нет — попробуйте указать только 1–2 ID реально пройденных
маршрутов через запятую, например `1,2`.

**Тёмная тема не переключилась.**
Переключатель внизу sidebar-а («Тема: …») меняет глобальный stylesheet —
эффект мгновенный. Если выглядит «полупримененным», свернуть-развернуть окно
обычно достаточно (Qt пересчитывает стиль).

## Лицензия

MIT (см. `pyproject.toml`). Демонстрационный учебный проект.
