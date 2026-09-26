"""Load the synthetic dataset into MySQL.

    python -m app.seed.seed            # refuses if employees already exist
    python -m app.seed.seed --reset    # wipes all app tables first

Run migrations first (alembic upgrade head); seeding never changes the schema.
"""

import argparse
import time
from collections.abc import Sequence

from sqlalchemy import Connection, Table, func, insert, select, text

from app.core.database import get_engine
from app.models import (
    Country,
    Department,
    Employee,
    FxRate,
    JobRole,
    Level,
    SalaryBand,
    SalaryRecord,
)
from app.seed import reference_data as ref
from app.seed.generator import Row, SeedData, generate

CHUNK_SIZE = 2_000

# Parents before children, so FKs hold during the insert.
LOAD_ORDER: list[tuple[type, str]] = [
    (Country, "countries"),
    (FxRate, "fx_rates"),
    (Department, "departments"),
    (JobRole, "job_roles"),
    (Level, "levels"),
    (SalaryBand, "salary_bands"),
    (Employee, "employees"),
    (SalaryRecord, "salary_records"),
]


def _insert(conn: Connection, table: Table, rows: Sequence[Row]) -> None:
    for start in range(0, len(rows), CHUNK_SIZE):
        conn.execute(insert(table), rows[start : start + CHUNK_SIZE])


def _reset(conn: Connection) -> None:
    # TRUNCATE is DDL in MySQL (implicit commit), so FK checks are relaxed only for
    # this connection and only for the wipe.
    conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
    try:
        for model, _ in reversed(LOAD_ORDER):
            conn.execute(text(f"TRUNCATE TABLE {model.__table__.name}"))
    finally:
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def load(data: SeedData, *, reset: bool) -> None:
    engine = get_engine()
    if reset:
        with engine.connect() as conn:
            _reset(conn)

    with engine.begin() as conn:  # one transaction: all or nothing
        existing = conn.execute(select(func.count()).select_from(Employee)).scalar_one()
        if existing:
            raise SystemExit(f"{existing} employees already present; rerun with --reset")
        for model, attr in LOAD_ORDER:
            _insert(conn, model.__table__, getattr(data, attr))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reset", action="store_true", help="wipe all app tables first")
    parser.add_argument("--seed", type=int, default=ref.DEFAULT_SEED)
    parser.add_argument("--employees", type=int, default=ref.DEFAULT_EMPLOYEE_COUNT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    data = generate(seed=args.seed, employee_count=args.employees)
    load(data, reset=args.reset)
    print(
        f"Seeded {len(data.employees)} employees, {len(data.salary_records)} salary records, "
        f"{len(data.salary_bands)} bands in {time.perf_counter() - started:.1f}s "
        f"(seed={args.seed}, as of {ref.AS_OF})"
    )


if __name__ == "__main__":
    main()
