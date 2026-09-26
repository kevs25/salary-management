"""Salary revisions: pay changes as effective-dated history, never an overwrite.

A revision closes the current record at the new effective date and opens a new
current record, in one transaction. This service owns the is_current invariant:
exactly one current record per employee, with no gaps or overlaps in history.
"""

from collections.abc import Callable
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.core.database import UnitOfWork
from app.core.exceptions import (
    CurrencyMismatch,
    EmployeeNotFound,
    InvalidEffectiveDate,
    InvalidSalaryRevision,
    MissingFxRate,
)
from app.models import Employee, EmployeeStatus, SalaryRecord
from app.schemas.salary import SalaryRecordOut, SalaryRevisionCreate, SalaryRevisionOut
from app.services.band import BandCell, BandResolver
from app.utils.currency import to_money, to_usd


class EmployeeLookup(Protocol):
    def get(self, entity_id: int) -> Employee | None: ...
    def country_currency(self, country_id: int) -> str | None: ...


class SalaryRecords(Protocol):
    def current_for_update(self, employee_id: int) -> SalaryRecord | None: ...
    def fx_rate(self, currency_code: str) -> Decimal | None: ...
    def add(self, entity: SalaryRecord) -> SalaryRecord: ...
    def flush(self) -> None: ...


class SalaryService:
    def __init__(
        self,
        employees: EmployeeLookup,
        salaries: SalaryRecords,
        bands: BandResolver,
        uow: UnitOfWork,
        today: Callable[[], date],
    ) -> None:
        self._employees = employees
        self._salaries = salaries
        self._bands = bands
        self._uow = uow
        self._today = today  # injected so rules about "the future" are testable

    def revise_salary(self, employee_id: int, payload: SalaryRevisionCreate) -> SalaryRevisionOut:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(f"Employee {employee_id} not found")
        if employee.status is EmployeeStatus.TERMINATED:
            raise InvalidSalaryRevision("Terminated employees cannot have their pay revised")

        currency = self._employees.country_currency(employee.country_id)
        if payload.currency_code is not None and payload.currency_code != currency:
            raise CurrencyMismatch(
                f"Pay for this employee is in {currency}, not {payload.currency_code}"
            )

        current = self._salaries.current_for_update(employee_id)
        if current is None:
            raise InvalidSalaryRevision(f"Employee {employee_id} has no current salary record")
        if current.currency_code != currency:
            # Can't happen through this API (country changes are blocked); guards data
            # loaded some other way from being silently mixed across currencies.
            raise CurrencyMismatch(
                f"Current pay is in {current.currency_code} but the employee's country "
                f"uses {currency}"
            )
        self._check_effective_date(payload.effective_from, current)

        base, bonus = to_money(payload.base_amount), to_money(payload.bonus_amount)
        if base == current.base_amount and bonus == current.bonus_amount:
            raise InvalidSalaryRevision("Revision does not change base or bonus")

        rate = self._salaries.fx_rate(currency)
        if rate is None:
            raise MissingFxRate(f"No FX snapshot rate for {currency}")
        resolved = self._bands.resolve(
            BandCell(
                department_id=employee.department_id,
                role_id=employee.role_id,
                level_id=employee.level_id,
                country_id=employee.country_id,
            )
        )

        # Close first and flush: the unique current index allows one current row.
        current.effective_to = payload.effective_from
        current.is_current = False
        self._salaries.flush()
        new = self._salaries.add(
            SalaryRecord(
                employee_id=employee_id,
                band_id=resolved.band.id if resolved else None,
                currency_code=currency,
                base_amount=base,
                bonus_amount=bonus,
                fx_rate_to_usd=rate,
                base_amount_usd=to_usd(base, rate),
                bonus_amount_usd=to_usd(bonus, rate),
                effective_from=payload.effective_from,
                effective_to=None,
                is_current=True,
                reason=payload.reason,
                note=payload.note,
            )
        )
        self._uow.commit()

        return SalaryRevisionOut(
            previous=SalaryRecordOut.model_validate(current),
            current=SalaryRecordOut.model_validate(new),
            base_change_pct=_percent_change(current.base_amount, base),
        )

    def _check_effective_date(self, effective_from: date, current: SalaryRecord) -> None:
        """Backdating is allowed only inside the current period.

        Starting on or before the current record would rewrite closed history;
        starting in the future would make is_current point at pay not yet in effect.
        """
        if effective_from <= current.effective_from:
            raise InvalidEffectiveDate(
                f"Revision must start after the current pay's start date "
                f"({current.effective_from}); earlier history is not rewritten"
            )
        if effective_from > self._today():
            raise InvalidEffectiveDate("Future-dated revisions are not supported")


def _percent_change(old: Decimal, new: Decimal) -> Decimal:
    return ((new - old) / old * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
