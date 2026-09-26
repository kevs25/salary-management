"""In-memory stand-ins for repositories and the unit of work. No database, no session.

ORM classes are used only as plain objects here (transient, never flushed), so
the service code under test sees the same types it gets in production.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.models import (
    Country,
    Department,
    Employee,
    JobRole,
    Level,
    SalaryBand,
    SalaryRecord,
)
from app.schemas.employee import EmployeeFilterOptions, EmployeeListItem, EmployeeQuery


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1


@dataclass
class FakeBandLookup:
    """Bands keyed by scope; None in role/country means a fallback band."""

    bands: dict[tuple[int, int, int | None, int | None], SalaryBand] = field(default_factory=dict)
    calls: list[tuple[int, int, int | None, int | None]] = field(default_factory=list)

    def add(
        self, *, department_id: int, level_id: int, role_id: int | None, country_id: int | None
    ) -> SalaryBand:
        band = SalaryBand(
            id=len(self.bands) + 1,
            department_id=department_id,
            role_id=role_id,
            level_id=level_id,
            country_id=country_id,
            currency_code="USD",
            min_amount=Decimal("80.00"),
            mid_amount=Decimal("100.00"),
            max_amount=Decimal("120.00"),
        )
        self.bands[(department_id, level_id, role_id, country_id)] = band
        return band

    def find_band(
        self, *, department_id: int, level_id: int, role_id: int | None, country_id: int | None
    ) -> SalaryBand | None:
        key = (department_id, level_id, role_id, country_id)
        self.calls.append(key)
        return self.bands.get(key)


class FakeEmployeeRepository:
    def __init__(self) -> None:
        self.departments: dict[int, Department] = {}
        self.roles: dict[int, JobRole] = {}
        self.levels: dict[int, Level] = {}
        self.countries: dict[int, Country] = {}
        self.employees: dict[int, Employee] = {}

    # Not exercised by the service rules; the SQL is covered by integration tests.
    def list(self, query: EmployeeQuery) -> tuple[list[EmployeeListItem], int]:
        raise NotImplementedError

    def filter_options(self) -> EmployeeFilterOptions:
        raise NotImplementedError

    def get(self, entity_id: int) -> Employee | None:
        return self.employees.get(entity_id)

    def get_detail(self, employee_id: int) -> Employee | None:
        employee = self.employees.get(employee_id)
        if employee is not None:
            employee.department = self.departments[employee.department_id]
            employee.role = self.roles[employee.role_id]
            employee.level = self.levels[employee.level_id]
            employee.country = self.countries[employee.country_id]
            employee.manager = self.employees[employee.manager_id] if employee.manager_id else None
        return employee

    def add(self, entity: Employee) -> Employee:
        entity.id = max(self.employees, default=0) + 1
        self.employees[entity.id] = entity
        return entity

    def code_exists(self, employee_code: str) -> bool:
        return any(e.employee_code == employee_code for e in self.employees.values())

    def email_taken(self, email: str, exclude_id: int | None = None) -> bool:
        return any(e.email == email and e.id != exclude_id for e in self.employees.values())

    def department_exists(self, department_id: int) -> bool:
        return department_id in self.departments

    def level_exists(self, level_id: int) -> bool:
        return level_id in self.levels

    def role_department_id(self, role_id: int) -> int | None:
        role = self.roles.get(role_id)
        return role.department_id if role else None

    def country_currency(self, country_id: int) -> str | None:
        country = self.countries.get(country_id)
        return country.currency_code if country else None

    def manager_id_of(self, employee_id: int) -> int | None:
        employee = self.employees.get(employee_id)
        return employee.manager_id if employee else None


class FakeSalaryRepository:
    def __init__(self, fx_rates: dict[str, Decimal] | None = None) -> None:
        self.records: list[SalaryRecord] = []
        self.fx_rates = fx_rates or {}

    def history(self, employee_id: int) -> list[SalaryRecord]:
        return sorted(
            (r for r in self.records if r.employee_id == employee_id),
            key=lambda r: r.effective_from,
            reverse=True,
        )

    def fx_rate(self, currency_code: str) -> Decimal | None:
        return self.fx_rates.get(currency_code)

    def add(self, entity: SalaryRecord) -> SalaryRecord:
        entity.id = len(self.records) + 1
        self.records.append(entity)
        return entity
