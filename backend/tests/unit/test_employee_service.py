from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import (
    DuplicateEmployee,
    EmployeeNotFound,
    InvalidEmployeeChange,
    InvalidReference,
    MissingFxRate,
)
from app.models import (
    ChangeReason,
    Country,
    Department,
    Employee,
    EmployeeStatus,
    JobRole,
    Level,
)
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services.band import BandResolver
from app.services.employee import EmployeeService
from tests.unit.fakes import (
    FakeBandLookup,
    FakeEmployeeRepository,
    FakeSalaryRepository,
    FakeUnitOfWork,
)

ENGINEERING, SALES = 1, 2
BACKEND, ACCOUNT_EXEC = 10, 20
L2, L3 = 2, 3
INDIA, US = 1, 2


class World:
    """A service wired to fakes, with a small org to validate against."""

    def __init__(self) -> None:
        self.employees = FakeEmployeeRepository()
        self.employees.departments = {
            ENGINEERING: Department(id=ENGINEERING, name="Engineering"),
            SALES: Department(id=SALES, name="Sales"),
        }
        self.employees.roles = {
            BACKEND: JobRole(id=BACKEND, name="Backend Engineer", department_id=ENGINEERING),
            ACCOUNT_EXEC: JobRole(id=ACCOUNT_EXEC, name="Account Executive", department_id=SALES),
        }
        self.employees.levels = {
            L2: Level(id=L2, code="L2", name="Intermediate", rank=2, min_years=2, max_years=5),
            L3: Level(id=L3, code="L3", name="Senior", rank=3, min_years=5, max_years=8),
        }
        self.employees.countries = {
            INDIA: Country(id=INDIA, code="IN", name="India", currency_code="INR"),
            US: Country(id=US, code="US", name="United States", currency_code="USD"),
        }
        self.salaries = FakeSalaryRepository(
            fx_rates={"INR": Decimal("0.01200000"), "USD": Decimal("1.00000000")}
        )
        self.bands = FakeBandLookup()
        self.uow = FakeUnitOfWork()
        self.service = EmployeeService(
            employees=self.employees,
            salaries=self.salaries,
            bands=BandResolver(self.bands),
            uow=self.uow,
        )

    def hire(self, **overrides: object) -> int:
        fields: dict[str, object] = {
            "employee_code": f"E{len(self.employees.employees) + 1:05d}",
            "first_name": "Asha",
            "last_name": "Rao",
            "email": f"asha{len(self.employees.employees) + 1}@acme.test",
            "department_id": ENGINEERING,
            "role_id": BACKEND,
            "level_id": L2,
            "country_id": INDIA,
            "hire_date": date(2025, 4, 1),
            "base_amount": Decimal("1500000.00"),
        }
        fields.update(overrides)
        return self.service.create_employee(EmployeeCreate.model_validate(fields)).id


@pytest.fixture
def world() -> World:
    return World()


class TestCreateEmployee:
    def test_creates_employee_with_current_hire_record_in_local_currency_and_usd(
        self, world: World
    ) -> None:
        band = world.bands.add(
            department_id=ENGINEERING, level_id=L2, role_id=None, country_id=INDIA
        )

        detail = world.service.create_employee(
            EmployeeCreate(
                employee_code="e00042",
                first_name=" Asha ",
                last_name="Rao",
                email="Asha.Rao@ACME.test",
                department_id=ENGINEERING,
                role_id=BACKEND,
                level_id=L2,
                country_id=INDIA,
                hire_date=date(2025, 4, 1),
                base_amount=Decimal("1500000.00"),
                bonus_amount=Decimal("150000.00"),
            )
        )

        assert detail.employee_code == "E00042"
        assert detail.first_name == "Asha"
        assert detail.email == "asha.rao@acme.test"
        assert detail.department.name == "Engineering"
        salary = detail.current_salary
        assert salary is not None
        assert salary.reason is ChangeReason.HIRE
        assert salary.currency_code == "INR"
        assert salary.base_amount == Decimal("1500000.00")
        assert salary.fx_rate_to_usd == Decimal("0.01200000")
        assert salary.base_amount_usd == Decimal("18000.00")
        assert salary.bonus_amount_usd == Decimal("1800.00")
        assert salary.effective_from == date(2025, 4, 1)
        assert salary.effective_to is None
        assert salary.band_id == band.id  # resolved through the fallback chain
        assert detail.salary_history == [salary]
        assert world.uow.commits == 1

    def test_links_no_band_when_no_policy_covers_the_cell(self, world: World) -> None:
        detail = world.service.get_employee(world.hire())

        assert detail.current_salary is not None
        assert detail.current_salary.band_id is None

    def test_rejects_duplicate_code(self, world: World) -> None:
        world.hire(employee_code="E00001")

        with pytest.raises(DuplicateEmployee):
            world.hire(employee_code="E00001")
        assert world.uow.commits == 1

    def test_rejects_duplicate_email(self, world: World) -> None:
        world.hire(email="asha@acme.test")

        with pytest.raises(DuplicateEmployee):
            world.hire(email="asha@acme.test")

    def test_rejects_role_from_another_department(self, world: World) -> None:
        with pytest.raises(InvalidReference, match="does not belong"):
            world.hire(department_id=ENGINEERING, role_id=ACCOUNT_EXEC)
        assert world.employees.employees == {}
        assert world.salaries.records == []
        assert world.uow.commits == 0

    @pytest.mark.parametrize(
        "overrides",
        [
            {"department_id": 99},
            {"role_id": 99},
            {"level_id": 99},
            {"country_id": 99},
            {"manager_id": 99},
        ],
    )
    def test_rejects_unknown_references(self, world: World, overrides: dict) -> None:
        with pytest.raises(InvalidReference):
            world.hire(**overrides)

    def test_rejects_currency_without_fx_snapshot_rate(self, world: World) -> None:
        del world.salaries.fx_rates["INR"]

        with pytest.raises(MissingFxRate):
            world.hire()
        assert world.uow.commits == 0


class TestGetEmployee:
    def test_unknown_employee_is_not_found(self, world: World) -> None:
        with pytest.raises(EmployeeNotFound):
            world.service.get_employee(404)


class TestUpdateEmployee:
    def test_applies_only_the_fields_sent(self, world: World) -> None:
        emp_id = world.hire(first_name="Asha")

        detail = world.service.update_employee(emp_id, EmployeeUpdate(level_id=L3))

        assert detail.level.code == "L3"
        assert detail.first_name == "Asha"
        assert world.uow.commits == 2  # hire + update

    def test_unknown_employee_is_not_found(self, world: World) -> None:
        with pytest.raises(EmployeeNotFound):
            world.service.update_employee(404, EmployeeUpdate(level_id=L3))

    def test_changing_country_requires_a_salary_revision(self, world: World) -> None:
        emp_id = world.hire(country_id=INDIA)

        with pytest.raises(InvalidEmployeeChange, match="salary revision"):
            world.service.update_employee(emp_id, EmployeeUpdate(country_id=US))
        assert world.employees.employees[emp_id].country_id == INDIA

    def test_resending_the_same_country_is_allowed(self, world: World) -> None:
        emp_id = world.hire(country_id=INDIA)

        world.service.update_employee(emp_id, EmployeeUpdate(country_id=INDIA))

    def test_moving_department_requires_a_role_from_that_department(self, world: World) -> None:
        emp_id = world.hire(department_id=ENGINEERING, role_id=BACKEND)

        with pytest.raises(InvalidReference):
            world.service.update_employee(emp_id, EmployeeUpdate(department_id=SALES))

        detail = world.service.update_employee(
            emp_id, EmployeeUpdate(department_id=SALES, role_id=ACCOUNT_EXEC)
        )
        assert detail.department.name == "Sales"
        assert detail.role.name == "Account Executive"

    def test_email_must_stay_unique_but_keeping_your_own_is_fine(self, world: World) -> None:
        first = world.hire(email="first@acme.test")
        second = world.hire(email="second@acme.test")

        with pytest.raises(DuplicateEmployee):
            world.service.update_employee(second, EmployeeUpdate(email="first@acme.test"))
        world.service.update_employee(first, EmployeeUpdate(email="first@acme.test"))

    def test_required_fields_cannot_be_cleared(self, world: World) -> None:
        emp_id = world.hire()

        with pytest.raises(InvalidEmployeeChange):
            world.service.update_employee(emp_id, EmployeeUpdate(first_name=None))

    def test_manager_can_be_set_and_cleared(self, world: World) -> None:
        boss = world.hire(level_id=L3)
        emp_id = world.hire()

        assert world.service.update_employee(emp_id, EmployeeUpdate(manager_id=boss)).manager
        cleared = world.service.update_employee(emp_id, EmployeeUpdate(manager_id=None))
        assert cleared.manager is None

    def test_employee_cannot_manage_themselves(self, world: World) -> None:
        emp_id = world.hire()

        with pytest.raises(InvalidReference, match="themselves"):
            world.service.update_employee(emp_id, EmployeeUpdate(manager_id=emp_id))

    def test_manager_cycles_are_rejected(self, world: World) -> None:
        top = world.hire()
        middle = world.hire(manager_id=top)
        bottom = world.hire(manager_id=middle)

        with pytest.raises(InvalidReference, match="cycle"):
            world.service.update_employee(top, EmployeeUpdate(manager_id=bottom))

    def test_status_change(self, world: World) -> None:
        emp_id = world.hire()

        detail = world.service.update_employee(
            emp_id, EmployeeUpdate(status=EmployeeStatus.TERMINATED)
        )
        assert detail.status is EmployeeStatus.TERMINATED


def test_employee_model_full_name() -> None:
    assert Employee(first_name="Asha", last_name="Rao").full_name == "Asha Rao"
