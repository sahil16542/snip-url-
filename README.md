# snip

A small URL shortener. FastAPI + SQLAlchemy + Postgres + Alembic.

## Stack

- **Python 3.12** (see [Two Pythons caveat](#two-pythons-caveat) below)
- **FastAPI** — HTTP layer
- **SQLAlchemy 2** (sync) + **psycopg 3** — DB access
- **Alembic** — migrations
- **Postgres** — storage

See [`DECISIONS.md`](DECISIONS.md) for the reasoning behind the driver
choice, schema, and base62 implementation.

## Setup

```bash
git clone <this repo>
cd snip
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root:

```
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/snip
```

If your password contains special characters (e.g. `@`), URL-encode them
(`%40` for `@`).

Create the database and apply migrations:

```bash
createdb snip
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

Then:

- Health check: <http://127.0.0.1:8000/health>
- Interactive API docs: <http://127.0.0.1:8000/docs>

## Tests

```bash
pytest
```

## Migrations

```bash
# generate a new migration from model changes
alembic revision --autogenerate -m "describe change"

# apply
alembic upgrade head

# roll back one step
alembic downgrade -1

# where are we
alembic current
```

## Layout

```
app/
  core/       app settings (loads .env)
  db/         SQLAlchemy Base + session factory
  models/     ORM models
  routers/    HTTP routers (empty for now)
  schemas/    Pydantic schemas (empty for now)
  services/   pure logic — base62, etc.
  main.py     FastAPI app
alembic/      migration env + versions/
tests/        pytest tests
```

## Two Pythons caveat

The repo's `venv/` was initially built against Python 3.9 while the
system `alembic` runs on 3.12. Both work today, but pick one and rebuild
the venv against it to avoid drift:

```bash
rm -rf venv
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
