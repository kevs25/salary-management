"""In-memory stand-ins for repositories and the unit of work. No database, no session.

ORM classes are used only as plain objects here (transient, never flushed), so
the service code under test sees the same types it gets in production.
"""

from dataclasses import dataclass, field
from datetime import datetime
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
        self,
        *,
        department_id: int,
        level_id: int,
        role_id: int | None,
        country_id: int | None,
        currency_code: str = "USD",
        amounts: tuple[str, str, str] = ("80.00", "100.00", "120.00"),
    ) -> SalaryBand:
        band = SalaryBand(
            id=len(self.bands) + 1,
            department_id=department_id,
            role_id=role_id,
            level_id=level_id,
            country_id=country_id,
            currency_code=currency_code,
            min_amount=Decimal(amounts[0]),
            mid_amount=Decimal(amounts[1]),
            max_amount=Decimal(amounts[2]),
        )
        self.bands[(department_id, level_id, role_id, country_id)] = band
        return band

    def find_band(
        self, *, department_id: int, level_id: int, role_id: int | None, country_id: int | None
    ) -> SalaryBand | None:
        key = (department_id, level_id, role_id, country_id)
        self.calls.append(key)
        return self.bands.get(key)


class FakeReferenceRepository:
    def __init__(self) -> None:
        self.departments: dict[int, Department] = {}
        self.roles: dict[int, JobRole] = {}
        self.levels: dict[int, Level] = {}
        self.countries: dict[int, Country] = {}

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


class FakeEmployeeRepository:
    def __init__(self, references: FakeReferenceRepository) -> None:
        self.references = references
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
            employee.department = self.references.departments[employee.department_id]
            employee.role = self.references.roles[employee.role_id]
            employee.level = self.references.levels[employee.level_id]
            employee.country = self.references.countries[employee.country_id]
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

    def current_for_update(self, employee_id: int) -> SalaryRecord | None:
        return next(
            (r for r in self.records if r.employee_id == employee_id and r.is_current), None
        )

    def fx_rate(self, currency_code: str) -> Decimal | None:
        return self.fx_rates.get(currency_code)

    def add(self, entity: SalaryRecord) -> SalaryRecord:
        # Mirrors the unique index on current_employee_id in MySQL.
        if entity.is_current and self.current_for_update(entity.employee_id) is not None:
            raise AssertionError(f"second current record for employee {entity.employee_id}")
        entity.id = len(self.records) + 1
        self.records.append(entity)
        return entity

    def flush(self) -> None:
        pass


class FakeBandRepository:
    """Bands keyed by id; scope uniqueness is left to the service, as in production."""

    def __init__(self, references: FakeReferenceRepository) -> None:
        self.references = references
        self.bands: dict[int, SalaryBand] = {}
        self.referenced: set[int] = set()  # band ids some salary record points at

    def find_band(
        self, *, department_id: int, level_id: int, role_id: int | None, country_id: int | None
    ) -> SalaryBand | None:
        return next(
            (
                b
                for b in self.bands.values()
                if (b.department_id, b.level_id, b.role_id, b.country_id)
                == (department_id, level_id, role_id, country_id)
            ),
            None,
        )

    def list(self, query: object) -> tuple[list[SalaryBand], int]:
        raise NotImplementedError  # SQL covered by integration tests

    def get(self, entity_id: int) -> SalaryBand | None:
        return self.bands.get(entity_id)

    def get_detail(self, band_id: int) -> SalaryBand | None:
        band = self.bands.get(band_id)
        if band is not None:
            refs = self.references
            band.department = refs.departments[band.department_id]
            band.level = refs.levels[band.level_id]
            band.role = refs.roles[band.role_id] if band.role_id else None
            band.country = refs.countries[band.country_id] if band.country_id else None
            band.updated_at = datetime(2026, 9, 1)
        return band

    def add(self, entity: SalaryBand) -> SalaryBand:
        entity.id = max(self.bands, default=0) + 1
        self.bands[entity.id] = entity
        return entity

    def is_referenced(self, band_id: int) -> bool:
        return band_id in self.referenced

    def delete(self, band: SalaryBand) -> None:
        del self.bands[band.id]
