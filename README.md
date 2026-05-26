# Tourist Club — ИС туристического клуба

Итоговый проект по курсу «Базы данных» (вариант 4.17).
Стек: **Python 3.12 + PySide6 + SQLAlchemy 2.0 + PostgreSQL 16**.

Документация:
- [docs/specification.md](docs/specification.md) — что именно строим (контракт реализации).
- [docs/plan.md](docs/plan.md) — план работ по этапам.
- [docs/er-diagram.md](docs/er-diagram.md) — финальная схема БД.
- [docs/task.md](docs/task.md), [docs/requirements.md](docs/requirements.md) — исходное ТЗ.

## Состояние

**Этап 8** — SQL-консоль с read-only / full режимами, явным commit/rollback,
историей запросов и экспортом в CSV. Заглушки остались только у разделов
«Администрирование» и «Сервисный режим».

## Локальная разработка

Требуется: Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker.

```bash
git clone <repo>
cd papuan-database
cp .env.example .env                          # отредактируйте пароли перед первым `docker compose up`
docker compose up -d                          # Postgres (5432) + Adminer (http://localhost:8080)
uv sync                                       # установка зависимостей
uv run alembic upgrade head                   # накат всех миграций (схема + триггеры + admin)
uv run python -m app.cli check-db --readonly  # проверка подключения (RW + RO)
uv run python -m app                          # запуск GUI
```

## Миграции

Список накатанных миграций — `uv run alembic current`, история — `uv run alembic history`.
Откат на одну ступень: `uv run alembic downgrade -1`.

## Качество кода

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Подробнее о соглашениях — `docs/specification.md` §6.3 (кодстайл) и §5.6 (UI).
