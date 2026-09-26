# ACME Salary Management

A web app for ACME's HR Manager to maintain salary data for ~10,000 employees across
six countries, and to answer how the org pays people - replacing a spreadsheet.

## What it does

- **Employees** - server-side search, filters (department, role, level, country, status, USD salary range), sortable columns, pagination; create and edit employees.
- **Employee detail** - current pay, where it sits in the band (compa-ratio, gap), salary history timeline, salary revision.
- **Dashboard** - headcount, payroll cost, median and average pay, band compliance and median compa-ratio; pay by department / country / level / role; compa-ratio quartiles per group.

Behind it, a FastAPI service keeps salary as effective-dated history, resolves each
employee's pay band through a fallback chain, and computes every aggregate in SQL.

## Run it

```sh
docker compose up --build -d                                   # MySQL + API on :8000
docker compose run --rm api python -m app.seed.seed --reset    # 10,000 demo employees (~3s)
cd frontend && npm install && npm run dev                      # web app on :5173
```

API docs: http://localhost:8000/docs.

## Tests

```sh
docker compose run --rm api pytest                  # backend: unit + integration on MySQL
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

## Stack

Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, MySQL 8 · React, TypeScript, Vite, Mantine,
TanStack Query, Recharts · Docker Compose.
