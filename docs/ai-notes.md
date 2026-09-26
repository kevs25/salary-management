# AI Usage Log

How AI (Claude Code) was used on this project: what was delegated, what was decided by hand, and what the AI got wrong and had corrected.

## Decided by hand (before any code)

Written up in `REQUIREMENTS.md`, `DESIGN.md` and `CLAUDE.md` before the AI touched code:

- The data model, including salary as effective-dated history rather than a column on Employee.
- Local currency plus normalised USD on every amount, using a committed FX snapshot.
- The band fallback chain: dept+role+level+country, then dept+level+country, then dept+level.
- The denormalised `is_current` flag and the index plan.
- Scope cuts (payroll, RBAC, approvals, import, live FX, ...).

`CLAUDE.md` is the standing brief given to the AI. It restates these decisions as rules the AI must not violate.

## 2026-09-26: Backend scaffold

**Prompt:** "read CLAUDE.md, REQUIREMENTS.md and DESIGN.md, then scaffold the backend"

**Delegated:** project layout, settings, DB session, exception mapping, base repository, Alembic setup, Docker Compose, SQLAlchemy models, initial migration, test harness.

**Choices the AI made and flagged:**

- Code lives under `backend/` so `frontend/` can sit beside it. The layout inside matches CLAUDE.md.
- **Explicit UnitOfWork commit, no commit in dependency teardown.** Committing after `yield` in a FastAPI dependency can run after the response is built, so a failed commit could follow a 200. Services commit through an injected `UnitOfWork`. Unit tests can fake it.
- **Half-open salary periods** `[effective_from, effective_to)`. The next record's `effective_from` equals the previous one's `effective_to`, so there are no off-by-one days.
- **`fx_rate_to_usd` stored on each salary record,** so every USD figure can be traced to the rate used.

**Gaps in the spec that the AI caught:**

- **The planned unique key on `salary_bands(department_id, role_id, level_id, country_id)` would not enforce uniqueness for fallback bands.** Those have `role_id` / `country_id` NULL, and MySQL unique indexes treat NULLs as distinct. Fix: stored generated columns `role_key = COALESCE(role_id, 0)` and `country_key = COALESCE(country_id, 0)` carry the unique index.
- **The `is_current` invariant was only enforced in application code.** Added a stored generated column `current_employee_id = IF(is_current, employee_id, NULL)` with a unique index, so MySQL itself rejects a second current record. A CHECK also ties `is_current` to `effective_to IS NULL`.

**What the AI got wrong and corrected:**

- It first declared `salary_records.employee_id` with `ON DELETE CASCADE`. MySQL forbids CASCADE on a base column of a stored generated column, and cascading would also have deleted the salary audit trail. Changed to RESTRICT. Leavers use `status = terminated`.
- It first gave `band_id` `ON DELETE SET NULL`, which would silently drop the band reference from historical salary records. Changed to RESTRICT.
- The hand-written migration first produced doubled check-constraint names (`ck_salary_records_ck_salary_records_...`) because the metadata naming convention was applied on top of full names. Caught by rendering the migration as offline SQL. Fixed with `op.f()`. Migration DDL was then diffed line-by-line against the models' DDL and matches.
- The model declared the `(employee_id, effective_from DESC)` index with a raw `text("effective_from DESC")` element. Once Docker was up, `alembic check` against real MySQL reported it as permanent false drift, because Alembic can't compare text index elements. Re-declared with `SalaryRecord.effective_from.desc()`, which gives the same DDL and no drift. Caveat: MySQL reflection doesn't report index direction, so a future ASC/DESC change on this index won't show up in `alembic check`.

**Verified against MySQL 8.4 (Docker):** the migration downgrades and upgrades cleanly, the 5 schema-invariant integration tests pass (duplicate current record, `current_is_open` CHECK, duplicate NULL-scope band, band min > mid), `alembic check` reports no drift, and the full suite passes inside the `api` container.

## 2026-09-26: Backend structure corrected by hand

The AI's first layout followed DESIGN.md's *suggested* layout literally (`api/v1/`, `repositories/`, a separate `api/errors.py` and `core/unit_of_work.py`). It was replaced with a structure specified by hand:

- `core/settings.py`, `core/database.py` (singleton engine with an explicit `QueuePool`, session factory), `core/dependencies.py` (`get_db`, `get_*_service`), `core/exceptions.py` (domain exceptions plus their handler).
- `router/main_router.py` + `router/v1/<feature>_router.py`, `repository/`, and `utils/` for `pagination` and `currency`.

The AI kept two of its own decisions in the new layout. The explicit `UnitOfWork` moved into `core/database.py`. The engine is now created lazily via `get_engine()`, so importing the app in unit tests never touches the database. CLAUDE.md and DESIGN.md were updated to the new layout so the brief and the code agree.

## 2026-09-26: Seed script, band resolution, employee services

**Prompt:** "push the code; get method employees/filter after this move to seed script and reference data and employee services"

**Delegated:** seed reference data and calibration numbers, the generator, the bulk loader, band repository and resolver, employee schemas, repository, service and router, unit fakes, and all tests.

**Choices the AI made and flagged:**

- **The seed is split into a pure generator and a thin loader.** `generate()` returns row dicts with explicit ids, using a seeded RNG and a fixed `AS_OF` date. So the DESIGN.md seed sanity check runs as a unit test on the full 10k dataset with no database (0.3s). The loader bulk-inserts in one transaction and refuses a non-empty database without `--reset`.
- **Salary history is generated backwards from today's pay.** Pay rises are undone year by year (merit, promotion, market adjustment). This keeps the out-of-band placement of current pay exact: 4%, 200 below and 200 above.
- **Band resolution was built in this step, not deferred to the band feature,** because creating an employee creates the hire salary record, which links a band.
- **A profile edit can't change country.** The pay currency would silently go stale; that change belongs to a salary revision.
- **Known gap, to settle in analytics:** a PATCH that changes department, role or level doesn't re-link the current salary record's `band_id`. Band-compliance analytics should resolve the band from the employee's *current* placement. `band_id` on a record is then "the band when this pay was set", which is an audit fact.
- **`/employees/filters` returns reference lists plus the current USD salary range,** so the frontend can draw the range slider.

**What the AI got wrong and corrected:**

- The employee-code schema used `to_upper=True` with pattern `^[A-Z0-9-]...`. Pydantic checks the pattern *before* the case transform, so a lowercase code `e00042` was rejected instead of normalised. Caught by the unit test that sends lowercase input. The pattern now accepts either case.

**Verified at 10k employees (MySQL 8.4):** every employee endpoint responds in under 55ms (budget: 500ms). `EXPLAIN` shows the filtered list uses the composite `(department, country, level)` index and an `eq_ref` on `uq_salary_records_current_employee_id` for current pay.

## 2026-09-26: Salary revisions

**Prompt:** "push the code, then move to salary revisions"

**Delegated:** the revision service, schemas, endpoint, repository locking, and unit and integration tests.

**Rules the AI proposed (CLAUDE.md named the areas: overlapping dates, backdating, currency mismatch):**

- **Backdating is allowed only inside the current period.** A start on or before the current record's start would overlap or rewrite closed history, so it's rejected. Corrections to old history are out of scope; they would need their own audited flow.
- **No future-dated revisions.** A future start would make `is_current` point at pay not yet in effect. Scheduled raises would need a "pending" state, which is left out. "Today" comes from an injected clock (`get_today`), so unit and integration tests pin it.
- **Pay must stay in the country's currency.** An explicit `currency_code` that differs is a `CurrencyMismatch`. A current record in a different currency is also refused, as a guard against data loaded outside the API.
- Terminated employees and no-op revisions are refused. `hire` is not a revision reason.

**Concurrency:** the current row is read with `SELECT ... FOR UPDATE`, and the close is flushed before the insert. The unique index on the generated `current_employee_id` column is the final guarantee of one current record. The AI first claimed in a docstring that a blocked second revision "reads the record the first one created". That InnoDB behaviour wasn't verified, so the claim was softened to what the unique index actually guarantees.

**Open:** employee *creation* still accepts a future `hire_date`, which creates a current record that isn't in effect yet. That's inconsistent with the revision rule. Onboarding future hires is a real use case, so the call is left to the author.
