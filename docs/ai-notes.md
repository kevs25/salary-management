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

**Delegated:** the revision service, schemas, endpoint, repository locking, and unit and integration tests.

**Rules the AI proposed (CLAUDE.md named the areas: overlapping dates, backdating, currency mismatch):**

- **Backdating is allowed only inside the current period.** A start on or before the current record's start would overlap or rewrite closed history, so it's rejected. Corrections to old history are out of scope; they would need their own audited flow.
- **No future-dated revisions.** A future start would make `is_current` point at pay not yet in effect. Scheduled raises would need a "pending" state, which is left out. "Today" comes from an injected clock (`get_today`), so unit and integration tests pin it.
- **Pay must stay in the country's currency.** An explicit `currency_code` that differs is a `CurrencyMismatch`. A current record in a different currency is also refused, as a guard against data loaded outside the API.
- Terminated employees and no-op revisions are refused. `hire` is not a revision reason.

**Concurrency:** the current row is read with `SELECT ... FOR UPDATE`, and the close is flushed before the insert. The unique index on the generated `current_employee_id` column is the final guarantee of one current record. The AI first claimed in a docstring that a blocked second revision "reads the record the first one created". That InnoDB behaviour wasn't verified, so the claim was softened to what the unique index actually guarantees.

**Open:** employee *creation* still accepts a future `hire_date`, which creates a current record that isn't in effect yet. That's inconsistent with the revision rule. Onboarding future hires is a real use case, so the call is left to the author.

## 2026-09-26: CSV export dropped, band management

**Decided by hand:** CSV export removed from scope. It was deleted from REQUIREMENTS.md (later items renumbered) and CLAUDE.md; DESIGN.md never mentioned it. CSV *import* stays listed as out of scope.

**Delegated:** a refactor moving reference lookups out of `EmployeeRepository` into `repository/reference.py`, so band validation doesn't depend on the employee repository. Also the band service, API, and tests.

**Choices the AI made and flagged:**

- **`BandScope` is defined once on the model.** Resolver strategies are named by it, and the API returns it. A role-specific band without a country is refused: resolution never looks one up, so it would be dead policy.
- **Band currency is derived, not sent.** It's the country's currency, or USD for a department-wide band.
- **Scope is immutable; only amounts are edited.** A different scope is a different band.
- **Delete is allowed only if no salary record was ever priced against the band.** Salary history keeps its band link as an audit fact. Editing a band is the normal path.
- **Known trade-off:** band *edits* are not effective-dated. Changing a band's amounts changes policy for everyone from now on, and the previous amounts are not kept. Compliance and compa-ratio will read today's bands. Band history is not needed for any listed feature, so it's left out; `updated_at` records when a band last changed.

**Verified:** 153 tests pass (110 unit, 43 integration). `alembic check` shows no drift after adding relationships. The band list over 900 bands responds in 7–16ms.

## 2026-09-26: Analytics

**Delegated:** analytics schemas, SQL, service, endpoints, per-employee pay assessment on the employee detail, and unit and integration tests.

**Choices the AI made and flagged:**

- **Population:** non-terminated employees at their current pay; on-leave people count. Pay statistics use base pay in USD; payroll cost is base + bonus in USD. Band comparisons use base pay only.
- **The band is resolved live, in SQL, from each employee's placement today.** Three outer joins in fallback order, each probing the unique band-scope index. The `band_id` stored on a salary record means "the band when this pay was set". This settles the open question from the employee-services entry: a promotion or department move is judged against the new band immediately.
- **Pay is compared in the band's currency.** It's the local amount when the currencies match, so min/max boundaries compare exactly. Otherwise (department-wide USD bands) it's the USD amount converted at the snapshot rate and rounded to cents, the same way in SQL and in Python.
- **Medians and quartiles use `ROW_NUMBER()` windows with linear interpolation** (the `PERCENTILE_CONT` definition, which MySQL lacks). Histogram buckets are conditional sums. Nothing is aggregated in Python.
- **The SQL/Python split follows CLAUDE.md** ("aggregate in SQL" plus "unit-test compa-ratio and boundaries"). The per-employee rules (band position with inclusive min/max, compa-ratio to 4 dp, gap) are pure Python functions, unit-tested at exact boundaries. The SQL uses the same comparisons. An integration test pins the SQL to the same semantics: pay at min/max is within the band, one cent outside is not.
- **An integration test checks the analytics SQL against an independent oracle,** computed row by row with Python's `statistics` module on a 300-employee generated dataset. It covers headcount, payroll, mean, median, quartiles, histogram, compliance counts and the out-of-band list.

**What the AI got wrong or had to adjust:**

- The first draft used `PARTITION BY 0` (a constant) for the whole-population case. It was changed to an unpartitioned window before it ran, since MySQL's treatment of a constant there was uncertain.
- A stray `null` import and `__all__` entry were left in the repository module and removed.
- The first draft of the oracle test had a meaningless expression for the mean (`fmean(x) and sum(x)/len(x)`). It was caught on review before running.
- **Precision:** MySQL keeps 6 dp on `DECIMAL` division (`div_precision_increment` = 4, on top of the dividend's 2 dp). So SQL compa-ratios are compared to the oracle within 0.0001; money figures match exactly.

**Verified at 10k employees:** summary 158ms, breakdowns about 80ms, compa-ratio about 90ms, band compliance about 125ms (budget: 500ms). 194 tests pass (141 unit, 53 integration).

## 2026-09-26: Frontend

**Delegated:** the whole React app: scaffold, typed API client, query hooks, the five screens, charts, tests, the Docker/nginx service.

**Choices the AI made and flagged:**

- **Mantine** as the component library, which REQUIREMENTS.md left open: tables, forms, modals and the app shell with little custom CSS.
- **Types generated from FastAPI's OpenAPI schema** (`openapi-typescript` + `openapi-fetch`), per DESIGN.md's "single generated API client". TypeScript is pinned to 5.9 because the generator's peer range doesn't include 6. The alternative, forcing past the peer check, was rejected.
- **Filters, sort and page live in the URL** (DESIGN.md: shareable views). Changing a filter resets to page 1.
- **Money is never a float.** Amounts are formatted from the API's decimal strings (`Intl.NumberFormat` accepts numeric strings exactly), form inputs are validated text, and bodies are sent as strings. Numbers are used only for chart geometry. A test formats 2^53 + 1 exactly.
- **The chart** was designed with the dataviz skill. Pay by group is one validated hue in horizontal bars (a magnitude job; no rainbow on nominal categories), with a table showing the same figures. Refetches keep the previous render dimmed instead of flashing a skeleton.
- **The API is proxied to the same origin** (the Vite proxy in dev, nginx in Docker), so the backend needs no CORS setup to serve the SPA.

**Decided by hand after review:**

- **The compa-ratio section was removed from the dashboard.** The AI had built a diverging stacked bar per department (and re-stepped its palette after a validator failure), then a quartile table; both were cut to keep the dashboard to one question: how pay is spread. Compa-ratio stays visible per employee (detail page, compliance list) and as the median on the dashboard; the `/analytics/compa-ratio` endpoint is kept in the API.
- **The compliance page's Outside / Below min / Above max switch was removed.** The page lists everyone outside their band, and each row's badge says which side.
- **Frontend history was rewritten page by page** before pushing: scaffold, then Employees, Employee detail, Dashboard, Band compliance, Salary bands, Docker. Each commit builds and passes its tests, and the root README grows with each one.

**What the AI got wrong and corrected:**

- The first two frontend commits did not build on their own: the scaffold imported screens that arrived in the next commit. This was fixed by the page-by-page rewrite above.
- The first modal implementation reset form state in `useEffect` on open, which oxlint flagged for missing dependencies. It was replaced by mounting the form inside the modal, so each opening starts fresh with no effect.
- `DebouncedInput` first synced its draft with `setState` inside an effect. It was replaced by React's adjust-state-during-render pattern. The commit now also waits for the debounce to settle, so a stale value can't overwrite a back-button change.
- The band position track put a flat band (min = max) at 14% instead of the centre. Caught by a unit test and fixed.
- The band-delete dialog appended its own explanation to a backend message that already said the same thing; the duplicate was removed.

**Not verified:** the browser extension wasn't connected, so the screens were not visually inspected by the AI. What was verified: typecheck, lint, 43 unit and component tests, a production build, the dev server and proxy returning live data, and the Docker image serving the app, deep links and the proxied API.
