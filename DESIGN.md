# Design & Patterns Note

Companion to `REQUIREMENTS.md`. Records the architecture, the patterns used and why, and the trade-offs taken.

---

## 1. Architecture

A layered (clean-ish) monolith. One deployable backend, one SPA, one MySQL database.

```
React + TypeScript SPA
        │  REST/JSON
        ▼
FastAPI routers        ← HTTP only: validation, status codes, auth dependency
        ▼
Service layer          ← business rules: band resolution, revision rules, analytics
        ▼
Repository layer       ← all SQL / SQLAlchemy lives here
        ▼
MySQL 8 (InnoDB)
```

The rule that keeps this honest: **routers never touch the ORM session directly, and repositories never contain business rules.** Every rule worth testing sits in the service layer, which is why the unit tests are fast.

Backend layout:

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
    repository/          base, employee, salary, band, analytics
    utils/               pagination, currency
    seed/                seed.py + reference data
  alembic/
  tests/
    unit/                services with fake repositories, no DB
    integration/         API + real MySQL
```

## 2. Patterns Used

| Pattern | Where | Why |
|---|---|---|
| **Layered architecture** | Whole backend | Clear boundaries; each layer testable in isolation. |
| **Repository** | `repository/` | Isolates persistence. Lets unit tests inject in-memory fakes instead of spinning up MySQL — directly serves the "fast, deterministic tests" requirement. |
| **Dependency Injection** | FastAPI `Depends` | Sessions, repos, services and the current user are injected, not imported. Swapping a real repo for a fake in tests is a one-line override. |
| **DTO / Schema separation** | `schemas/` | Pydantic models are the API contract; ORM models are storage. Prevents accidental leakage of internal columns and lets the two evolve independently. |
| **Strategy** | Band resolution & analytics metrics | Resolving the band for an employee has fallbacks (exact `dept+role+level+country` → `dept+level+country` → `dept+level`). Each is a strategy tried in order, so the policy is readable and unit-testable instead of a nested `if` tree. Same shape for metric calculators (avg / median / p90). |
| **Specification / query-object** | `repository/employee.list()` | Filters (department, country, level, salary range, search) compose into one query object rather than a combinatorial explosion of finder methods. |
| **Unit of Work** | Session-per-request | A salary revision closes the previous record and opens a new one — must be atomic. One transaction commits or rolls back the whole operation. |
| **Factory** | Seed script | `EmployeeFactory` / `SalaryFactory` produce coherent synthetic records from a seeded RNG, so the 10k dataset is reproducible run to run. |
| **CQRS-lite** | `repository/analytics` | Writes go through the ORM; analytics are hand-written aggregate SQL returning flat read models. Forcing dashboard queries through ORM objects at 10k rows is how you get N+1s. |
| **Custom exception → handler mapping** | `core/exceptions` | Services raise domain errors (`BandNotFound`, `InvalidEffectiveDate`); one FastAPI exception handler maps them to HTTP codes. Services stay framework-agnostic. |

On the frontend: container/presentational split, TanStack Query as the server-state cache (URL-synced filters so any view is shareable), and a single generated API client so types come from one place.

## 3. MySQL Specifics

- **InnoDB**, `utf8mb4`, all money as `DECIMAL(14,2)` — never `FLOAT`.
- **Indexes for the actual query patterns:** `employees(department_id, country_id, level_id)` composite for the filtered list; `employees(employee_code)` unique; `salary_records(employee_id, effective_from DESC)`; a partial-equivalent index on `salary_records(is_current)` for current-pay joins; `salary_bands(department_id, role_id, level_id, country_id)` unique.
- **Current salary is denormalised** onto a `is_current` flag (maintained transactionally) so the list view is a single join instead of a correlated subquery per row. Deliberate read-optimisation with a clearly owned invariant.
- **MySQL 8 window functions** for median (`PERCENTILE`-style via `ROW_NUMBER`) and compa-ratio distributions — computed in the DB, not in Python.
- **Alembic** for every schema change; the seed script is separate from migrations.
- Keyset or bounded offset pagination with `LIMIT` — never load 10k rows into the app.

## 4. Trade-offs Taken

- **Monolith over microservices.** One team, one bounded context. Splitting this would add network failure modes and buy nothing.
- **MySQL over SQLite** (the brief allowed either). Costs a Docker dependency in tests; buys concurrency, window functions and production realism. Mitigated by making unit tests DB-free via the repository fakes and running integration tests against a containerised MySQL.
- **Denormalised `is_current` flag.** Costs an invariant to maintain on every revision; buys a materially simpler and faster list query at 10k rows.
- **FX snapshot over live rates.** Costs freshness; buys reproducible, testable analytics.
- **No bulk importer.** Costs a migration convenience; buys focus on the workflow and analytics that the assessment actually asks to be done well.

## 5. Testing Strategy

- **Unit (majority, no DB):** band resolution incl. every fallback; compa-ratio and out-of-band detection at exact boundaries; salary revision rules (overlapping effective dates, backdating, currency mismatch); analytics maths on fixed fixtures. Fake repositories, seeded data, no clock dependency — deterministic by construction.
- **Integration:** API contract tests per endpoint against a real MySQL with a small fixture set; pagination/filter correctness; transaction rollback on failure.
- **Seed sanity check:** an assertion-style test that the generated 10k dataset is coherent (every employee resolves to a band, no negative pay, a deliberate small % of out-of-band outliers so the compliance screen has something to show).

## 6. AI Usage (for the artifacts folder)

Keep a `docs/ai-notes.md` recording: what was delegated (scaffolding, CRUD boilerplate, seed generation, test skeletons, chart components) versus what was decided by hand (the data model, the effective-dating approach, index design, the band-resolution fallback chain, out-of-scope calls). Include the prompts that produced non-trivial output, and note anything the AI got wrong that you corrected — that correction record is usually the most credible evidence of engineering judgement in the whole submission.