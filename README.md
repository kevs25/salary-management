# ACME Salary Management

A web app for ACME's HR Manager to maintain salary data for ~10,000 employees across
six countries, and to answer how the org pays people - replacing a spreadsheet.

## What it does

- **Employees** - server-side search, filters (department, role, level, country, status, USD salary range), sortable columns, pagination; create and edit employees.
- **Employee detail** - current pay, where it sits in the band (compa-ratio, gap), salary history timeline, salary revision.
- **Dashboard** - headcount, payroll cost, median and average pay, band compliance and median compa-ratio; pay by department / country / level / role.
- **Band compliance** - everyone paid below their band minimum or above its maximum, most severe first, each a link to the employee.
- **Salary bands** - the pay policy: filter, create (including department-wide fallback bands), edit amounts, delete unused bands.

Behind it, a FastAPI service keeps salary as effective-dated history, resolves each
employee's pay band through a fallback chain, and computes every aggregate in SQL.

## Run it

The database is a managed MySQL 8 on Aiven. Put its URL and CA certificate in
`backend/.env` and `backend/ca.pem`; both are gitignored, and
[backend/README.md](backend/README.md#database) has the steps. Then:

```sh
docker compose up --build -d                            # API and web app
docker compose run --rm api python -m app.seed.seed     # 10,000 demo employees, once
```

Open **http://localhost:8080**. API docs: http://localhost:8000/docs.

## Tests

```sh
docker compose run --rm api pytest               # backend: unit (+ integration with a *_test DB)
cd frontend && npm test                          # unit + component tests, no network
```

## Decisions worth knowing

- **Salary is history, not a column.** A revision closes the current record and opens a
  new one in one transaction; MySQL itself allows only one current record per employee.
- **Local currency plus USD on every amount**, converted with a committed FX snapshot,
  so cross-country figures are reproducible.
- **Bands resolve most-specific-first**: role + country, then all roles in the country,
  then department-wide. Compliance uses the band for where someone sits *today*.
- **Aggregation happens in SQL** (medians via window functions); every list and
  analytics endpoint answers in under 200ms at 10,000 employees.
- **Money is never a float** - `DECIMAL(14,2)` in MySQL, decimal strings in the UI.

## Documentation

- [REQUIREMENTS.md](REQUIREMENTS.md) - scope, what is out of scope and why
- [DESIGN.md](DESIGN.md) - architecture, patterns, trade-offs
- [docs/ai-notes.md](docs/ai-notes.md) - what was delegated to AI, what was decided by hand, what was corrected
- [backend/README.md](backend/README.md) - running and testing the API
- [frontend/README.md](frontend/README.md) - how the web app is put together

## How it was built

Requirements and design were written first, then the backend and the web app were built
feature by feature, with AI assistance for most of the code. The commit history shows the
order; [docs/ai-notes.md](docs/ai-notes.md) records which decisions were made by hand and
what the AI got wrong along the way.

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, MySQL 8 (Aiven) · React, TypeScript, Vite, Mantine,
TanStack Query, Recharts · Docker Compose.
