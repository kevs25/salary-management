# CLAUDE.md

Context for Claude Code working in this repo.

## What this is

An assessment submission: employee salary management software for an org with 10,000 employees. The user persona is the HR Manager of ACME org, who currently manages salary data for employees across multiple countries in Excel. The software must let them manage that data and answer questions about how the org pays people.

Graded on: clarity of thinking, architecture and design decisions, clean maintainable code, meaningful fast tests, intentional AI use, and product thinking. Not on complexity.

Read `REQUIREMENTS.md` and `DESIGN.md` before writing code. `docs/requirements-notes.md` is the author's own pre-build notes.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest
- Database: MySQL 8 (InnoDB)
- Frontend: React + TypeScript + Vite, TanStack Query, Recharts
- Database: managed MySQL 8 on Aiven (no local database container)
- Docker Compose runs the API and frontend

## Architecture rules (do not violate)

Layers: `router -> service -> repository -> MySQL`.

- Routers handle HTTP only. They never touch the ORM session directly.
- All business rules live in services. All SQL lives in repositories.
- Services raise domain exceptions from `core/exceptions.py`; the one handler registered there maps them to HTTP codes. Services never import FastAPI or build responses.
- Pydantic schemas are the API contract, SQLAlchemy models are storage. Never return ORM objects from a router.

Layout:

```
backend/
  app/
    main.py              FastAPI init, middleware, exception handlers
    core/
      settings.py        Pydantic BaseSettings, reads env
      database.py        singleton engine + QueuePool, session factory, UnitOfWork
      dependencies.py    get_db, get_*_service
      exceptions.py      domain exceptions + the handler mapping them to HTTP
    models/              SQLAlchemy tables
    schemas/             employee, salary, band, analytics, common
    router/
      main_router.py     mounts /api/v1
      v1/                employee_router, salary_router, band_router, analytics_router
    services/            employee, salary, band, analytics
    repository/          base, reference, employee, salary, band, analytics
    utils/               pagination, currency
    seed/                seed.py + reference data
  alembic/
  tests/
    unit/                services with fake repositories, no DB
    integration/         API + real MySQL
```

Frontend (`frontend/`): conventions are in `frontend/README.md` - generated API types (`npm run api:types` after any API change), filters in the URL, money as decimal strings, charts from `src/lib/chartColors.ts`.

## Domain model

Country (code, name, currency), Department, JobRole, Level (L1-L5 with experience ranges), SalaryBand, Employee, SalaryRecord, FxRate.

Non-obvious decisions, keep them:

- **SalaryBand** is keyed on `(department, role, level, country)` and holds `min / mid / max` in local currency. This is the org's pay policy.
- **Salary is effective-dated history, not a column on Employee.** A revision closes the previous record and opens a new one, in one transaction. Never overwrite.
- **`SalaryRecord.is_current`** is a denormalised flag maintained transactionally, so the 10k-row list view is a single join rather than a correlated subquery. Whoever writes the revision logic owns this invariant.
- **Every amount stores local currency plus a normalised USD value** using a committed FX snapshot (not a live API), so cross-country analytics are reproducible.
- **Band resolution has an ordered fallback chain**: exact `dept+role+level+country`, then `dept+level+country`, then `dept+level`. Implement as ordered strategies, not nested ifs.
- Money is `DECIMAL(14,2)`. Never float.

## Features

CRUD: paginated server-side searchable employee list (filters: department, country, level, role, salary range; sortable), employee detail with salary history timeline, create/edit employee, salary revision, band management.

Analytics: headcount, total payroll cost (USD), avg/median salary, breakdowns by department / country / level / role, band compliance (paid below min or above max), compa-ratio (salary / band mid) per employee.

Explicitly out of scope, do not build: payroll/payslips/tax, RBAC and multi-role auth, approval workflows, Excel import, live FX, equity/benefits/leave/performance, multi-tenancy, i18n, forecasting.

## Performance

List and analytics endpoints must respond under 500ms at 10,000 employees.

- Aggregate in SQL, never in Python. Use MySQL 8 window functions for median and compa-ratio distributions.
- Indexes: `employees(department_id, country_id, level_id)` composite, `employees(employee_code)` unique, `salary_records(employee_id, effective_from DESC)`, index on `salary_records(is_current)`, `salary_bands(department_id, role_id, level_id, country_id)` unique.
- No N+1. Paginate with LIMIT, never load 10k rows into the app.

## Testing

- Unit tests must not require a database. Inject fake repositories. Target: band resolution including every fallback, compa-ratio and out-of-band detection at exact boundaries, salary revision rules (overlapping effective dates, backdating, currency mismatch), analytics maths on fixed fixtures.
- Integration tests hit the API against real MySQL, in a separate database whose name ends in `_test`. They drop and re-migrate it, and refuse any other database.
- Deterministic: seeded RNG, no wall-clock dependency.

## Seed script

10,000 employees, 8 departments, 6 countries, 5 levels, ~30 roles. Seeded RNG so runs are reproducible. Bands calibrated per country so figures look plausible.

**Deliberately place 3-5% of employees outside their band** so the band-compliance screen has real content in the demo.

## Commits

Incremental commits that show evolution are part of the grade. Small, scoped, conventional-style messages. Commit the requirements and design docs first, before any code.

## AI usage log

Maintain `docs/ai-notes.md`: what was delegated (scaffolding, CRUD boilerplate, seed generation, test skeletons, charts) vs decided by hand (data model, effective dating, index design, band fallback chain, scope cuts). Record the decisions and anything the AI got wrong that was corrected; do not paste chat prompts verbatim.