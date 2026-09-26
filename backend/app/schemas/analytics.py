from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models import BandScope
from app.utils.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams


class Dimension(StrEnum):
    DEPARTMENT = "department"
    COUNTRY = "country"
    LEVEL = "level"
    ROLE = "role"


class BandPosition(StrEnum):
    BELOW = "below"
    WITHIN = "within"
    ABOVE = "above"
    NO_BAND = "no_band"


class OutOfBandFilter(StrEnum):
    BELOW = "below"
    ABOVE = "above"
    OUTSIDE = "outside"  # below or above


# Queries


class AnalyticsFilter(BaseModel):
    """Narrows the population: employees who are not terminated, at current pay."""

    model_config = ConfigDict(extra="forbid")

    department_id: int | None = None
    role_id: int | None = None
    level_id: int | None = None
    country_id: int | None = None


class BreakdownQuery(AnalyticsFilter):
    by: Dimension


class CompaRatioQuery(AnalyticsFilter):
    by: Dimension = Dimension.DEPARTMENT


class BandComplianceQuery(AnalyticsFilter):
    position: OutOfBandFilter = OutOfBandFilter.OUTSIDE
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE

    @property
    def page_params(self) -> PageParams:
        return PageParams(page=self.page, page_size=self.page_size)

    @property
    def filters(self) -> AnalyticsFilter:
        return AnalyticsFilter.model_validate(
            self.model_dump(include={"department_id", "role_id", "level_id", "country_id"})
        )


# Raw read models: what the analytics repository's SQL returns, before the service
# rounds amounts and derives percentages.


@dataclass(frozen=True)
class PayStatsRow:
    key: int | None
    name: str
    headcount: int
    payroll_cost_usd: Decimal
    avg_base_usd: Decimal | None
    median_base_usd: Decimal | None
    min_base_usd: Decimal | None
    max_base_usd: Decimal | None
    below_band: int
    within_band: int
    above_band: int
    no_band: int


@dataclass(frozen=True)
class CompaStatsRow:
    key: int | None
    name: str
    employees_with_band: int
    avg: Decimal | None
    p25: Decimal | None
    median: Decimal | None
    p75: Decimal | None
    min: Decimal | None
    max: Decimal | None
    bucket_counts: tuple[int, ...]


@dataclass(frozen=True)
class OutOfBandRow:
    employee_id: int
    employee_code: str
    first_name: str
    last_name: str
    department: str
    role: str
    level: str
    country_code: str
    currency_code: str
    base_amount: Decimal
    band_id: int
    band_scope: BandScope
    band_currency_code: str
    band_min: Decimal
    band_mid: Decimal
    band_max: Decimal
    salary_in_band_currency: Decimal


# Responses


class GroupKey(BaseModel):
    id: int | None = Field(description="null for the whole population")
    name: str


class SalaryStats(BaseModel):
    """Annual base pay in USD across the group."""

    avg: Decimal | None
    median: Decimal | None
    min: Decimal | None
    max: Decimal | None


class BandCompliance(BaseModel):
    below: int
    within: int
    above: int
    no_band: int
    compliance_pct: Decimal | None = Field(
        description="within / employees with a band, percent; null if none have a band"
    )


class PaySummary(BaseModel):
    headcount: int
    payroll_cost_usd: Decimal = Field(description="annual base + bonus, USD")
    base_salary_usd: SalaryStats
    band_compliance: BandCompliance
    compa_ratio_median: Decimal | None
    fx_as_of: date | None = Field(description="date of the FX snapshot behind every USD figure")


class BreakdownRow(BaseModel):
    group: GroupKey
    headcount: int
    payroll_cost_usd: Decimal
    payroll_share_pct: Decimal | None
    base_salary_usd: SalaryStats
    band_compliance: BandCompliance


class Breakdown(BaseModel):
    by: Dimension
    rows: list[BreakdownRow]


class CompaBucket(BaseModel):
    label: str
    lower: Decimal | None = Field(description="inclusive; null = unbounded")
    upper: Decimal | None = Field(description="exclusive; null = unbounded")
    count: int


class CompaRatioRow(BaseModel):
    group: GroupKey
    employees_with_band: int
    avg: Decimal | None
    p25: Decimal | None
    median: Decimal | None
    p75: Decimal | None
    min: Decimal | None
    max: Decimal | None
    buckets: list[CompaBucket]


class CompaRatioDistribution(BaseModel):
    by: Dimension
    rows: list[CompaRatioRow]


class BandRef(BaseModel):
    id: int
    scope: BandScope
    currency_code: str
    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal


class PayAssessment(BaseModel):
    """Where one employee's base pay sits against the band that applies to them."""

    band: BandRef
    salary_in_band_currency: Decimal
    compa_ratio: Decimal
    position: BandPosition
    gap_amount: Decimal = Field(description="distance outside the band, band currency; 0 inside")
    gap_pct: Decimal = Field(description="gap as a percent of the breached boundary; 0 inside")


class OutOfBandEmployee(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    department: str
    role: str
    level: str
    country_code: str
    currency_code: str
    base_amount: Decimal
    assessment: PayAssessment
