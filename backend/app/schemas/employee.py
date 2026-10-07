from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.models import EmployeeStatus
from app.schemas.analytics import PayAssessment
from app.schemas.common import CountryOut, DepartmentOut, LevelOut, Money, RoleOut, Schema
from app.schemas.salary import SalaryRecordOut
from app.utils.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=128, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    ),
]
EmployeeCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z0-9-]{3,16}$")
]


class EmployeeSort(StrEnum):
    NAME = "name"
    EMPLOYEE_CODE = "employee_code"
    HIRE_DATE = "hire_date"
    DEPARTMENT = "department"
    COUNTRY = "country"
    LEVEL = "level"
    BASE_SALARY_USD = "base_salary_usd"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class EmployeeQuery(BaseModel):
    """Filters, sort and page for the employee list, bound from query parameters.

    One query object, composed into one SQL statement by the repository, rather
    than a finder method per filter combination.
    """

    model_config = ConfigDict(extra="forbid")

    q: Annotated[str | None, Field(max_length=100, description="name, code or email")] = None
    department_id: int | None = None
    role_id: int | None = None
    level_id: int | None = None
    country_id: int | None = None
    status: EmployeeStatus | None = None
    min_salary_usd: Annotated[Decimal | None, Field(ge=0, description="current base, USD")] = None
    max_salary_usd: Annotated[Decimal | None, Field(ge=0, description="current base, USD")] = None
    sort: EmployeeSort = EmployeeSort.NAME
    order: SortOrder = SortOrder.ASC
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE

    @model_validator(mode="after")
    def _salary_range_ordered(self) -> Self:
        if (
            self.min_salary_usd is not None
            and self.max_salary_usd is not None
            and self.min_salary_usd > self.max_salary_usd
        ):
            raise ValueError("min_salary_usd must not exceed max_salary_usd")
        return self

    @property
    def page_params(self) -> PageParams:
        return PageParams(page=self.page, page_size=self.page_size)


class EmployeeListItem(Schema):
    """Flat read model for one row of the list: employee + names + current pay."""

    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    department_id: int
    department: str
    role_id: int
    role: str
    level_id: int
    level: str
    country_id: int
    country_code: str
    status: EmployeeStatus
    hire_date: date
    currency_code: str
    base_amount: Decimal
    bonus_amount: Decimal
    base_amount_usd: Decimal


class EmployeeFilterOptions(Schema):
    """Everything the list screen needs to render its filter controls."""

    departments: list[DepartmentOut]
    roles: list[RoleOut]
    levels: list[LevelOut]
    countries: list[CountryOut]
    statuses: list[EmployeeStatus]
    salary_usd_min: Decimal | None
    salary_usd_max: Decimal | None


class EmployeeRef(Schema):
    id: int
    employee_code: str
    full_name: str


class NetPay(Schema):
    """Current base pay after the flat tax deduction, in the salary's local currency."""

    currency_code: str
    base_amount: Money
    tax_rate: Decimal = Field(description="fraction deducted, e.g. 0.10")
    tax_amount: Money
    net_amount: Money = Field(description="base_amount - tax_amount")


class EmployeeDetail(Schema):
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: str
    hire_date: date
    status: EmployeeStatus
    department: DepartmentOut
    role: RoleOut
    level: LevelOut
    country: CountryOut
    manager: EmployeeRef | None
    current_salary: SalaryRecordOut | None
    net_pay: NetPay | None = Field(description="current base pay after tax; null if no salary")
    pay_assessment: PayAssessment | None = Field(
        description="current base pay against the band that applies today; null if none"
    )
    salary_history: list[SalaryRecordOut] = Field(description="newest first")


class EmployeeCreate(BaseModel):
    """A new hire. Their first salary record (reason=hire) is created with them."""

    model_config = ConfigDict(extra="forbid")

    employee_code: EmployeeCode
    first_name: Name
    last_name: Name
    email: Email
    department_id: int
    role_id: int
    level_id: int
    country_id: int
    manager_id: int | None = None
    hire_date: date
    status: EmployeeStatus = EmployeeStatus.ACTIVE
    base_amount: Annotated[Money, Field(gt=0, description="annual, local currency")]
    bonus_amount: Annotated[Money, Field(ge=0, description="annual, local currency")] = Decimal("0")


class EmployeeUpdate(BaseModel):
    """Partial profile update. Pay changes go through a salary revision instead.

    Only fields present in the request are applied; send manager_id: null to clear it.
    """

    model_config = ConfigDict(extra="forbid")

    first_name: Name | None = None
    last_name: Name | None = None
    email: Email | None = None
    department_id: int | None = None
    role_id: int | None = None
    level_id: int | None = None
    country_id: int | None = None
    manager_id: int | None = None
    status: EmployeeStatus | None = None
