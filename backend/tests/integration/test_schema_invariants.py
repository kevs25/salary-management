"""The invariants the schema enforces on its own, independent of service code."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.models import (
    ChangeReason,
    Country,
    Department,
    Employee,
    JobRole,
    Level,
    SalaryBand,
    SalaryRecord,
)

MYSQL_DUPLICATE_KEY = 1062
MYSQL_CHECK_VIOLATED = 3819


def _mysql_error_code(exc_info: pytest.ExceptionInfo[DBAPIError]) -> int:
    return exc_info.value.orig.args[0]


@pytest.fixture
def employee(db_session: Session) -> Employee:
    dept = Department(name="Engineering")
    country = Country(code="IN", name="India", currency_code="INR")
    level = Level(code="L1", name="Associate", rank=1, min_years=0, max_years=2)
    db_session.add_all([dept, country, level])
    db_session.flush()
    role = JobRole(department_id=dept.id, name="Backend Engineer")
    db_session.add(role)
    db_session.flush()
    emp = Employee(
        employee_code="E00001",
        first_name="Asha",
        last_name="Rao",
        email="asha.rao@acme.test",
        department_id=dept.id,
        role_id=role.id,
        level_id=level.id,
        country_id=country.id,
        hire_date=date(2024, 1, 1),
    )
    db_session.add(emp)
    db_session.flush()
    return emp


def _record(employee_id: int, start: date, end: date | None) -> SalaryRecord:
    return SalaryRecord(
        employee_id=employee_id,
        currency_code="INR",
        base_amount=Decimal("1200000.00"),
        fx_rate_to_usd=Decimal("0.01200000"),
        base_amount_usd=Decimal("14400.00"),
        effective_from=start,
        effective_to=end,
        is_current=end is None,
        reason=ChangeReason.HIRE,
    )


def test_closed_history_plus_one_current_record_is_allowed(
    db_session: Session, employee: Employee
) -> None:
    db_session.add_all(
        [
            _record(employee.id, date(2024, 1, 1), date(2025, 1, 1)),
            _record(employee.id, date(2025, 1, 1), date(2026, 1, 1)),
            _record(employee.id, date(2026, 1, 1), None),
        ]
    )
    db_session.flush()


def test_second_current_record_for_an_employee_is_rejected(
    db_session: Session, employee: Employee
) -> None:
    db_session.add(_record(employee.id, date(2024, 1, 1), None))
    db_session.flush()

    db_session.add(_record(employee.id, date(2025, 1, 1), None))
    with pytest.raises(DBAPIError) as exc_info:
        db_session.flush()
    assert _mysql_error_code(exc_info) == MYSQL_DUPLICATE_KEY


def test_current_record_with_an_end_date_is_rejected(
    db_session: Session, employee: Employee
) -> None:
    record = _record(employee.id, date(2024, 1, 1), date(2025, 1, 1))
    record.is_current = True

    db_session.add(record)
    with pytest.raises(DBAPIError) as exc_info:
        db_session.flush()
    assert _mysql_error_code(exc_info) == MYSQL_CHECK_VIOLATED


def _dept_level_band(employee: Employee) -> SalaryBand:
    # role_id and country_id left NULL: the last fallback in band resolution.
    return SalaryBand(
        department_id=employee.department_id,
        level_id=employee.level_id,
        currency_code="USD",
        min_amount=Decimal("10000.00"),
        mid_amount=Decimal("15000.00"),
        max_amount=Decimal("20000.00"),
    )


def test_duplicate_fallback_band_with_null_scope_is_rejected(
    db_session: Session, employee: Employee
) -> None:
    db_session.add(_dept_level_band(employee))
    db_session.flush()

    db_session.add(_dept_level_band(employee))
    with pytest.raises(DBAPIError) as exc_info:
        db_session.flush()
    assert _mysql_error_code(exc_info) == MYSQL_DUPLICATE_KEY


def test_band_with_min_above_mid_is_rejected(db_session: Session, employee: Employee) -> None:
    band = _dept_level_band(employee)
    band.min_amount = Decimal("16000.00")

    db_session.add(band)
    with pytest.raises(DBAPIError) as exc_info:
        db_session.flush()
    assert _mysql_error_code(exc_info) == MYSQL_CHECK_VIOLATED
