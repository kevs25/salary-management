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

## 2026-09-26: Backend structure corrected by hand

The AI's first layout followed DESIGN.md's *suggested* layout literally (`api/v1/`, `repositories/`, a separate `api/errors.py` and `core/unit_of_work.py`). It was replaced with a structure specified by hand:

- `core/settings.py`, `core/database.py` (singleton engine with an explicit `QueuePool`, session factory), `core/dependencies.py` (`get_db`, `get_*_service`), `core/exceptions.py` (domain exceptions plus their handler).
- `router/main_router.py` + `router/v1/<feature>_router.py`, `repository/`, and `utils/` for `pagination` and `currency`.

The AI kept two of its own decisions in the new layout. The explicit `UnitOfWork` moved into `core/database.py`. The engine is now created lazily via `get_engine()`, so importing the app in unit tests never touches the database. CLAUDE.md and DESIGN.md were updated to the new layout so the brief and the code agree.
