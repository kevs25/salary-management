# Backend

FastAPI + SQLAlchemy 2.0 + MySQL 8. Layers: `router -> service -> repository -> MySQL` (see `../DESIGN.md`).

## Database

A managed MySQL 8 on Aiven; nothing runs a local database. Configure it once:

1. Copy `.env.example` to `.env` (gitignored) and fill in `APP_DATABASE_URL`, using the
   plain URL. Aiven's `?ssl-mode=REQUIRED` is a MySQL-CLI option that PyMySQL rejects.
2. Download the service's CA certificate from the Aiven console to `backend/ca.pem`
   (gitignored) and set `APP_DB_SSL_CA` to its path.

## Run with Docker

From the repo root:

```sh
docker compose up --build -d                                   # API on :8000, web app on :8080
docker compose run --rm api python -m app.seed.seed            # load the 10k demo dataset once
```

The API container reads `backend/.env`, mounts `backend/ca.pem` as `/srv/ca.pem`, and
runs `alembic upgrade head` on start.

## Run locally

```sh
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # .venv/bin/pip on macOS/Linux
.venv/Scripts/alembic upgrade head
.venv/Scripts/python -m app.seed.seed      # refuses a non-empty database; --reset wipes it
.venv/Scripts/uvicorn app.main:app --reload
```

## Tests

```sh
pytest -m "not integration"   # unit only, no database, runs anywhere
pytest                        # integration tests too, when APP_TEST_DATABASE_URL is set
```

Integration tests drop and re-migrate their database on every run, then roll back each
test's transaction. So `APP_TEST_DATABASE_URL` must point at a **separate** database whose
name ends in `_test` (e.g. create `salary_test` on the Aiven service). The suite refuses to
run against anything else, so it can never wipe the real data.
