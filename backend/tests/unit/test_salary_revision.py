from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import (
    CurrencyMismatch,
    EmployeeNotFound,
    InvalidEffectiveDate,
    InvalidSalaryRevision,
    MissingFxRate,
)
from app.models import ChangeReason, Country, Employee, EmployeeStatus, SalaryRecord
from app.schemas.salary import SalaryRevisionCreate
from app.services.band import BandResolver
from app.services.salary import SalaryService
from tests.unit.fakes import (
    FakeBandLookup,
    FakeEmployeeRepository,
    FakeSalaryRepository,
    FakeUnitOfWork,
)

TODAY = date(2026, 9, 1)
HIRED = date(2024, 4, 1)
LAST_RAISE = date(2025, 4, 1)
EMP_ID, INDIA, ENGINEERING, BACKEND, L2 = 1, 1, 1, 10, 2


class World:
    def __init__(self) -> None:
        self.employees = FakeEmployeeRepository()
        self.employees.countries = {
            INDIA: Country(id=INDIA, code="IN", name="India", currency_code="INR")
        }
        self.employees.employees[EMP_ID] = Employee(
            id=EMP_ID,
            department_id=ENGINEERING,
            role_id=BACKEND,
            level_id=L2,
            country_id=INDIA,
            status=EmployeeStatus.ACTIVE,
        )
        self.salaries = FakeSalaryRepository(fx_rates={"INR": Decimal("0.01200000")})
        self.salaries.records = [
            _record(1, HIRED, LAST_RAISE, Decimal("1000000.00"), ChangeReason.HIRE),
            _record(2, LAST_RAISE, None, Decimal("1100000.00"), ChangeReason.MERIT),
        ]
        self.bands = FakeBandLookup()
        self.uow = FakeUnitOfWork()
        self.service = SalaryService(
            employees=self.employees,
            salaries=self.salaries,
            bands=BandResolver(self.bands),
            uow=self.uow,
            today=lambda: TODAY,
        )

    def revise(self, **overrides: object):
        fields: dict[str, object] = {
            "base_amount": "1210000.00",
            "effective_from": "2026-04-01",
            "reason": "merit",
        }
        fields.update(overrides)
        return self.service.revise_salary(EMP_ID, SalaryRevisionCreate.model_validate(fields))

    def history(self) -> list[SalaryRecord]:
        return sorted(self.salaries.records, key=lambda r: r.effective_from)


def _record(
    record_id: int, start: date, end: date | None, base: Decimal, reason: ChangeReason
) -> SalaryRecord:
    return SalaryRecord(
        id=record_id,
        employee_id=EMP_ID,
        band_id=None,
        currency_code="INR",
        base_amount=base,
        bonus_amount=Decimal("0.00"),
        fx_rate_to_usd=Decimal("0.01200000"),
        base_amount_usd=base * Decimal("0.012"),
        bonus_amount_usd=Decimal("0.00"),
        effective_from=start,
        effective_to=end,
        is_current=end is None,
        reason=reason,
        note=None,
    )


@pytest.fixture
def world() -> World:
    return World()


class TestRevision:
    def test_closes_current_record_and_opens_a_new_one(self, world: World) -> None:
        band = world.bands.add(
            department_id=ENGINEERING, level_id=L2, role_id=BACKEND, country_id=INDIA
        )

        result = world.revise(bonus_amount="50000.00", note="FY26 cycle")

        previous, current = result.previous, result.current
        assert previous.effective_to == date(2026, 4, 1)
        assert previous.is_current is False
        assert current.effective_from == date(2026, 4, 1)
        assert current.effective_to is None
        assert current.is_current is True
        assert current.reason is ChangeReason.MERIT
        assert current.note == "FY26 cycle"
        assert current.currency_code == "INR"
        assert current.base_amount_usd == Decimal("14520.00")
        assert current.bonus_amount_usd == Decimal("600.00")
        assert current.band_id == band.id
        assert result.base_change_pct == Decimal("10.00")
        assert world.uow.commits == 1

    def test_history_stays_contiguous_with_one_current_record(self, world: World) -> None:
        world.revise(effective_from="2026-04-01")
        world.revise(base_amount="1300000.00", effective_from="2026-07-01", reason="promotion")

        history = world.history()
        assert [r.is_current for r in history] == [False, False, False, True]
        for earlier, later in zip(history, history[1:], strict=False):
            assert earlier.effective_to == later.effective_from
        assert history[-1].effective_to is None

    def test_pay_cut_reports_a_negative_change(self, world: World) -> None:
        result = world.revise(base_amount="990000.00", reason="correction")

        assert result.base_change_pct == Decimal("-10.00")


class TestEffectiveDate:
    def test_backdating_inside_the_current_period_is_allowed(self, world: World) -> None:
        result = world.revise(effective_from="2025-04-02")  # day after current start

        assert result.previous.effective_to == date(2025, 4, 2)

    def test_revision_effective_today_is_allowed(self, world: World) -> None:
        world.revise(effective_from=TODAY.isoformat())

    @pytest.mark.parametrize(
        "effective_from",
        [
            LAST_RAISE.isoformat(),  # same day as the current record: would overlap it
            "2025-03-31",  # inside closed history
            HIRED.isoformat(),  # the hire date
            "2020-01-01",  # before hire
        ],
    )
    def test_starting_on_or_before_the_current_record_is_rejected(
        self, world: World, effective_from: str
    ) -> None:
        with pytest.raises(InvalidEffectiveDate, match="after the current"):
            world.revise(effective_from=effective_from)
        _assert_untouched(world)

    def test_future_dated_revision_is_rejected(self, world: World) -> None:
        with pytest.raises(InvalidEffectiveDate, match="Future"):
            world.revise(effective_from="2026-09-02")  # day after TODAY
        _assert_untouched(world)


class TestCurrency:
    def test_explicit_matching_currency_is_accepted_case_insensitively(self, world: World) -> None:
        assert world.revise(currency_code="inr").current.currency_code == "INR"

    def test_other_currency_is_rejected(self, world: World) -> None:
        with pytest.raises(CurrencyMismatch):
            world.revise(currency_code="USD")
        _assert_untouched(world)

    def test_current_record_in_a_different_currency_is_rejected(self, world: World) -> None:
        world.salaries.records[-1].currency_code = "USD"

        with pytest.raises(CurrencyMismatch):
            world.revise()

    def test_missing_fx_rate_is_rejected(self, world: World) -> None:
        world.salaries.fx_rates.clear()

        with pytest.raises(MissingFxRate):
            world.revise()
        _assert_untouched(world)


class TestPreconditions:
    def test_unknown_employee(self, world: World) -> None:
        with pytest.raises(EmployeeNotFound):
            world.service.revise_salary(
                404,
                SalaryRevisionCreate(
                    base_amount=Decimal("1"), effective_from=TODAY, reason=ChangeReason.MERIT
                ),
            )

    def test_terminated_employee(self, world: World) -> None:
        world.employees.employees[EMP_ID].status = EmployeeStatus.TERMINATED

        with pytest.raises(InvalidSalaryRevision, match="Terminated"):
            world.revise()

    def test_on_leave_employee_can_be_revised(self, world: World) -> None:
        world.employees.employees[EMP_ID].status = EmployeeStatus.ON_LEAVE

        world.revise()

    def test_employee_without_current_record(self, world: World) -> None:
        world.salaries.records.clear()

        with pytest.raises(InvalidSalaryRevision, match="no current"):
            world.revise()

    def test_revision_that_changes_nothing_is_rejected(self, world: World) -> None:
        with pytest.raises(InvalidSalaryRevision, match="does not change"):
            world.revise(base_amount="1100000.00", bonus_amount="0")
        _assert_untouched(world)


class TestPayloadValidation:
    @pytest.mark.parametrize(
        "overrides",
        [
            {"reason": "hire"},  # hires are created with the employee
            {"base_amount": "0"},
            {"base_amount": "-1"},
            {"bonus_amount": "-1"},
            {"base_amount": "100.001"},  # more precision than DECIMAL(14,2)
            {"currency_code": "RUPEE"},
            {"surprise": 1},
        ],
    )
    def test_rejected_by_schema(self, overrides: dict) -> None:
        fields = {"base_amount": "1.00", "effective_from": "2026-04-01", "reason": "merit"}
        fields.update(overrides)

        with pytest.raises(ValidationError):
            SalaryRevisionCreate.model_validate(fields)


def _assert_untouched(world: World) -> None:
    history = world.history()
    assert len(history) == 2
    assert history[-1].is_current is True
    assert history[-1].effective_to is None
    assert world.uow.commits == 0
