from decimal import Decimal
from typing import Protocol

from app.core.database import UnitOfWork
from app.core.exceptions import (
    DuplicateEmployee,
    EmployeeNotFound,
    InvalidEmployeeChange,
    InvalidReference,
    MissingFxRate,
)
from app.models import ChangeReason, Employee, SalaryRecord
from app.schemas.analytics import BandRef, PayAssessment
from app.schemas.common import Page
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeDetail,
    EmployeeFilterOptions,
    EmployeeListItem,
    EmployeeQuery,
    EmployeeUpdate,
)
from app.schemas.salary import SalaryRecordOut
from app.services.analytics import assess, salary_in_band_currency
from app.services.band import BandCell, BandResolver
from app.services.tax import net_pay
from app.utils.currency import to_money, to_usd

# Manager chains are short (L1 -> L5); anything longer than this is a cycle or bad data.
MAX_MANAGER_DEPTH = 50


class EmployeeRepositoryPort(Protocol):
    def list(self, query: EmployeeQuery) -> tuple[list[EmployeeListItem], int]: ...
    def filter_options(self) -> EmployeeFilterOptions: ...
    def get(self, entity_id: int) -> Employee | None: ...
    def get_detail(self, employee_id: int) -> Employee | None: ...
    def add(self, entity: Employee) -> Employee: ...
    def code_exists(self, employee_code: str) -> bool: ...
    def email_taken(self, email: str, exclude_id: int | None = None) -> bool: ...
    def manager_id_of(self, employee_id: int) -> int | None: ...


class ReferenceLookup(Protocol):
    def department_exists(self, department_id: int) -> bool: ...
    def level_exists(self, level_id: int) -> bool: ...
    def role_department_id(self, role_id: int) -> int | None: ...
    def country_currency(self, country_id: int) -> str | None: ...


class SalaryRepositoryPort(Protocol):
    def history(self, employee_id: int) -> list[SalaryRecord]: ...
    def fx_rate(self, currency_code: str) -> Decimal | None: ...
    def add(self, entity: SalaryRecord) -> SalaryRecord: ...


class EmployeeService:
    def __init__(
        self,
        employees: EmployeeRepositoryPort,
        references: ReferenceLookup,
        salaries: SalaryRepositoryPort,
        bands: BandResolver,
        uow: UnitOfWork,
    ) -> None:
        self._employees = employees
        self._references = references
        self._salaries = salaries
        self._bands = bands
        self._uow = uow

    # Reads

    def list_employees(self, query: EmployeeQuery) -> Page[EmployeeListItem]:
        items, total = self._employees.list(query)
        return Page(items=items, total=total, page=query.page, page_size=query.page_size)

    def filter_options(self) -> EmployeeFilterOptions:
        return self._employees.filter_options()

    def get_employee(self, employee_id: int) -> EmployeeDetail:
        employee = self._employees.get_detail(employee_id)
        if employee is None:
            raise EmployeeNotFound(f"Employee {employee_id} not found")
        history = [SalaryRecordOut.model_validate(r) for r in self._salaries.history(employee_id)]
        current = next((r for r in history if r.is_current), None)
        return EmployeeDetail.model_validate(
            {
                **{f: getattr(employee, f) for f in _PROFILE_FIELDS},
                "department": employee.department,
                "role": employee.role,
                "level": employee.level,
                "country": employee.country,
                "manager": employee.manager,
                "current_salary": current,
                "net_pay": net_pay(current.base_amount, current.currency_code) if current else None,
                "pay_assessment": self._assess(employee, current),
                "salary_history": history,
            }
        )

    def _assess(self, employee: Employee, current: SalaryRecordOut | None) -> PayAssessment | None:
        """Band is resolved from where the employee sits today, not from current.band_id."""
        if current is None:
            return None
        resolved = self._bands.resolve(
            BandCell(
                department_id=employee.department_id,
                role_id=employee.role_id,
                level_id=employee.level_id,
                country_id=employee.country_id,
            )
        )
        if resolved is None:
            return None
        band = resolved.band
        rate = self._salaries.fx_rate(band.currency_code)
        if rate is None:
            return None
        salary = salary_in_band_currency(
            base_amount=current.base_amount,
            base_amount_usd=current.base_amount_usd,
            salary_currency=current.currency_code,
            band_currency=band.currency_code,
            band_rate_to_usd=rate,
        )
        return assess(
            salary,
            BandRef(
                id=band.id,
                scope=resolved.strategy.scope,
                currency_code=band.currency_code,
                min_amount=band.min_amount,
                mid_amount=band.mid_amount,
                max_amount=band.max_amount,
            ),
        )

    # Writes

    def create_employee(self, payload: EmployeeCreate) -> EmployeeDetail:
        if self._employees.code_exists(payload.employee_code):
            raise DuplicateEmployee(f"Employee code {payload.employee_code} is already in use")
        if self._employees.email_taken(payload.email):
            raise DuplicateEmployee(f"Email {payload.email} is already in use")
        currency = self._check_placement(
            payload.department_id, payload.role_id, payload.level_id, payload.country_id
        )
        if payload.manager_id is not None and self._employees.get(payload.manager_id) is None:
            raise InvalidReference(f"Manager {payload.manager_id} does not exist")
        rate = self._salaries.fx_rate(currency)
        if rate is None:
            raise MissingFxRate(f"No FX snapshot rate for {currency}")

        employee = self._employees.add(
            Employee(
                employee_code=payload.employee_code,
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=payload.email,
                department_id=payload.department_id,
                role_id=payload.role_id,
                level_id=payload.level_id,
                country_id=payload.country_id,
                manager_id=payload.manager_id,
                hire_date=payload.hire_date,
                status=payload.status,
            )
        )
        resolved = self._bands.resolve(
            BandCell(
                department_id=payload.department_id,
                role_id=payload.role_id,
                level_id=payload.level_id,
                country_id=payload.country_id,
            )
        )
        base, bonus = to_money(payload.base_amount), to_money(payload.bonus_amount)
        self._salaries.add(
            SalaryRecord(
                employee_id=employee.id,
                band_id=resolved.band.id if resolved else None,
                currency_code=currency,
                base_amount=base,
                bonus_amount=bonus,
                fx_rate_to_usd=rate,
                base_amount_usd=to_usd(base, rate),
                bonus_amount_usd=to_usd(bonus, rate),
                effective_from=payload.hire_date,
                effective_to=None,
                is_current=True,
                reason=ChangeReason.HIRE,
            )
        )
        self._uow.commit()
        return self.get_employee(employee.id)

    def update_employee(self, employee_id: int, payload: EmployeeUpdate) -> EmployeeDetail:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(f"Employee {employee_id} not found")
        changes = payload.model_dump(exclude_unset=True)

        for field in _NON_CLEARABLE_FIELDS:
            if field in changes and changes[field] is None:
                raise InvalidEmployeeChange(f"{field} cannot be cleared")

        if changes.get("country_id", employee.country_id) != employee.country_id:
            # Moving country changes the pay currency, which needs a salary revision
            # in the new currency; a profile edit must not leave pay in the old one.
            raise InvalidEmployeeChange(
                "Changing country requires a salary revision in the new currency"
            )
        if "email" in changes and self._employees.email_taken(changes["email"], employee_id):
            raise DuplicateEmployee(f"Email {changes['email']} is already in use")
        if {"department_id", "role_id", "level_id"} & changes.keys():
            self._check_placement(
                changes.get("department_id", employee.department_id),
                changes.get("role_id", employee.role_id),
                changes.get("level_id", employee.level_id),
                employee.country_id,
            )
        if changes.get("manager_id") is not None:
            self._check_manager(employee_id, changes["manager_id"])

        for field, value in changes.items():
            setattr(employee, field, value)
        self._uow.commit()
        return self.get_employee(employee_id)

    # Rules

    def _check_placement(
        self, department_id: int, role_id: int, level_id: int, country_id: int
    ) -> str:
        """Validate the org placement; returns the country's currency."""
        if not self._references.department_exists(department_id):
            raise InvalidReference(f"Department {department_id} does not exist")
        role_department = self._references.role_department_id(role_id)
        if role_department is None:
            raise InvalidReference(f"Role {role_id} does not exist")
        if role_department != department_id:
            raise InvalidReference(f"Role {role_id} does not belong to department {department_id}")
        if not self._references.level_exists(level_id):
            raise InvalidReference(f"Level {level_id} does not exist")
        currency = self._references.country_currency(country_id)
        if currency is None:
            raise InvalidReference(f"Country {country_id} does not exist")
        return currency

    def _check_manager(self, employee_id: int, manager_id: int) -> None:
        if manager_id == employee_id:
            raise InvalidReference("An employee cannot manage themselves")
        if self._employees.get(manager_id) is None:
            raise InvalidReference(f"Manager {manager_id} does not exist")
        # Walk up from the new manager; reaching this employee would close a loop.
        current: int | None = manager_id
        for _ in range(MAX_MANAGER_DEPTH):
            current = self._employees.manager_id_of(current)
            if current is None:
                return
            if current == employee_id:
                raise InvalidReference(
                    f"Employee {manager_id} reports to {employee_id}; that would be a cycle"
                )
        raise InvalidReference("Manager chain is too deep")


# Optional in EmployeeUpdate only so they can be omitted; an explicit null is an error.
_NON_CLEARABLE_FIELDS = (
    "first_name",
    "last_name",
    "email",
    "department_id",
    "role_id",
    "level_id",
    "country_id",
    "status",
)

_PROFILE_FIELDS = (
    "id",
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "hire_date",
    "status",
)
