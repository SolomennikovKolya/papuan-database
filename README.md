# Tourist Club — ИС туристического клуба

Итоговый проект по курсу «Базы данных» (вариант 4.17).
Стек: **Python 3.12 + PySide6 + SQLAlchemy 2.0 + PostgreSQL 16**.

Документация:
- [docs/specification.md](docs/specification.md) — что именно строим (контракт реализации).
- [docs/plan.md](docs/plan.md) — план работ по этапам.
- [docs/task.md](docs/task.md), [docs/requirements.md](docs/requirements.md) — исходное ТЗ.

## Состояние

**Этап 0** — скелет проекта. Запускается «Hello, Qt», поднимается БД.

## Локальная разработка

Требуется: Python 3.12+, [uv](https://docs.astral.sh/uv/), Docker.

```bash
git clone <repo>
cd papuan-database
cp .env.example .env              # отредактируйте пароли при необходимости
docker compose up -d              # Postgres (5432) + Adminer (http://localhost:8080)
uv sync                           # установка зависимостей
uv run python -m app              # запуск GUI
```

## Качество кода

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Подробнее о соглашениях — `docs/specification.md` §6.3 (кодстайл) и §5.6 (UI).
