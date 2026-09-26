from sqlalchemy import ColumnElement, Select, exists, func, or_, select
from sqlalchemy.orm import joinedload

from app.models import (
    Country,
    Department,
    Employee,
    EmployeeStatus,
    JobRole,
    Level,
    SalaryRecord,
)
from app.repository.base import SqlAlchemyRepository
from app.schemas.common import CountryOut, DepartmentOut, LevelOut, RoleOut
from app.schemas.employee import (
    EmployeeFilterOptions,
    EmployeeListItem,
    EmployeeQuery,
    EmployeeSort,
    SortOrder,
)

# Joining on current_employee_id (unique, NULL on closed records) picks each
# employee's single current salary row straight off an index.
_CURRENT_SALARY_JOIN = SalaryRecord.current_employee_id == Employee.id

_SORT_COLUMNS: dict[EmployeeSort, tuple[ColumnElement, ...]] = {
    EmployeeSort.NAME: (Employee.last_name, Employee.first_name),
    EmployeeSort.EMPLOYEE_CODE: (Employee.employee_code,),
    EmployeeSort.HIRE_DATE: (Employee.hire_date,),
    EmployeeSort.DEPARTMENT: (Department.name,),
    EmployeeSort.COUNTRY: (Country.name,),
    EmployeeSort.LEVEL: (Level.rank,),
    EmployeeSort.BASE_SALARY_USD: (SalaryRecord.base_amount_usd,),
}


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _conditions(query: EmployeeQuery) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for column, value in (
        (Employee.department_id, query.department_id),
        (Employee.role_id, query.role_id),
        (Employee.level_id, query.level_id),
        (Employee.country_id, query.country_id),
        (Employee.status, query.status),
    ):
        if value is not None:
            conditions.append(column == value)
    if query.min_salary_usd is not None:
        conditions.append(SalaryRecord.base_amount_usd >= query.min_salary_usd)
    if query.max_salary_usd is not None:
        conditions.append(SalaryRecord.base_amount_usd <= query.max_salary_usd)
    if query.q and query.q.strip():
        # Case-insensitive through the utf8mb4_0900_ai_ci collation.
        pattern = f"%{_escape_like(query.q.strip())}%"
        conditions.append(
            or_(
                func.concat(Employee.first_name, " ", Employee.last_name).like(pattern),
                Employee.employee_code.like(pattern),
                Employee.email.like(pattern),
            )
        )
    return conditions


class EmployeeRepository(SqlAlchemyRepository[Employee]):
    model = Employee

    def list(self, query: EmployeeQuery) -> tuple[list[EmployeeListItem], int]:
        conditions = _conditions(query)

        total = self.session.scalar(
            select(func.count())
            .select_from(Employee)
            .join(SalaryRecord, _CURRENT_SALARY_JOIN)
            .where(*conditions)
        )

        direction = (lambda c: c.desc()) if query.order is SortOrder.DESC else (lambda c: c.asc())
        order_by = [direction(c) for c in _SORT_COLUMNS[query.sort]] + [direction(Employee.id)]
        page = query.page_params
        rows = self.session.execute(
            self._list_select()
            .where(*conditions)
            .order_by(*order_by)
            .limit(page.limit)
            .offset(page.offset)
        ).mappings()
        return [EmployeeListItem.model_validate(dict(row)) for row in rows], total or 0

    @staticmethod
    def _list_select() -> Select:
        return (
            select(
                Employee.id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Employee.email,
                Employee.department_id,
                Department.name.label("department"),
                Employee.role_id,
                JobRole.name.label("role"),
                Employee.level_id,
                Level.code.label("level"),
                Employee.country_id,
                Country.code.label("country_code"),
                Employee.status,
                Employee.hire_date,
                SalaryRecord.currency_code,
                SalaryRecord.base_amount,
                SalaryRecord.bonus_amount,
                SalaryRecord.base_amount_usd,
            )
            .select_from(Employee)
            .join(Department, Department.id == Employee.department_id)
            .join(JobRole, JobRole.id == Employee.role_id)
            .join(Level, Level.id == Employee.level_id)
            .join(Country, Country.id == Employee.country_id)
            .join(SalaryRecord, _CURRENT_SALARY_JOIN)
        )

    def filter_options(self) -> EmployeeFilterOptions:
        salary_min, salary_max = self.session.execute(
            select(
                func.min(SalaryRecord.base_amount_usd), func.max(SalaryRecord.base_amount_usd)
            ).where(SalaryRecord.is_current.is_(True))
        ).one()
        return EmployeeFilterOptions(
            departments=[
                DepartmentOut.model_validate(d)
                for d in self.session.scalars(select(Department).order_by(Department.name))
            ],
            roles=[
                RoleOut.model_validate(r)
                for r in self.session.scalars(select(JobRole).order_by(JobRole.name))
            ],
            levels=[
                LevelOut.model_validate(lvl)
                for lvl in self.session.scalars(select(Level).order_by(Level.rank))
            ],
            countries=[
                CountryOut.model_validate(c)
                for c in self.session.scalars(select(Country).order_by(Country.name))
            ],
            statuses=list(EmployeeStatus),
            salary_usd_min=salary_min,
            salary_usd_max=salary_max,
        )

    def get_detail(self, employee_id: int) -> Employee | None:
        """The employee with department, role, level, country and manager loaded."""
        stmt = (
            select(Employee)
            .options(
                joinedload(Employee.department),
                joinedload(Employee.role),
                joinedload(Employee.level),
                joinedload(Employee.country),
                joinedload(Employee.manager),
            )
            .where(Employee.id == employee_id)
        )
        return self.session.scalars(stmt).one_or_none()

    def code_exists(self, employee_code: str) -> bool:
        return bool(
            self.session.scalar(select(exists().where(Employee.employee_code == employee_code)))
        )

    def email_taken(self, email: str, exclude_id: int | None = None) -> bool:
        condition = Employee.email == email
        if exclude_id is not None:
            condition = condition & (Employee.id != exclude_id)
        return bool(self.session.scalar(select(exists().where(condition))))

    # Reference lookups used to validate a payload's foreign keys.

    def department_exists(self, department_id: int) -> bool:
        return self.session.get(Department, department_id) is not None

    def level_exists(self, level_id: int) -> bool:
        return self.session.get(Level, level_id) is not None

    def role_department_id(self, role_id: int) -> int | None:
        role = self.session.get(JobRole, role_id)
        return role.department_id if role else None

    def country_currency(self, country_id: int) -> str | None:
        country = self.session.get(Country, country_id)
        return country.currency_code if country else None

    def manager_id_of(self, employee_id: int) -> int | None:
        return self.session.scalar(select(Employee.manager_id).where(Employee.id == employee_id))
