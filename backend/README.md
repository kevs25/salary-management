# Backend

FastAPI + SQLAlchemy 2.0 + MySQL 8. Layers: `router -> service -> repository -> MySQL` (see `../DESIGN.md`).

## Run with Docker

From the repo root:

```sh
docker compose up --build        # MySQL + API on http://localhost:8000 (docs at /docs)
docker compose run --rm api pytest   # unit + integration tests against the compose MySQL
```

The API container runs `alembic upgrade head` on start.

## Run locally

```sh
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # .venv/bin/pip on macOS/Linux
cp .env.example .env
docker compose up -d db                     # from the repo root
.venv/Scripts/alembic upgrade head
.venv/Scripts/uvicorn app.main:app --reload
```

## Tests

```sh
pytest -m "not integration"   # unit only, no database, runs anywhere
pytest                        # integration tests run when APP_TEST_DATABASE_URL is set
```

Integration tests migrate the `salary_test` schema from scratch (down, then up) on
every run and roll back each test's transaction.
