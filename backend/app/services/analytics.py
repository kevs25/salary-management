"""Pay analytics: how the org pays people, and how that compares with its bands.

Aggregation happens in SQL (repository/analytics.py). This module holds:
- the per-employee rules (band position, compa-ratio, gap), as pure functions
  unit-tested at the exact boundaries; the SQL uses the same comparisons
- assembly of the SQL results into responses: rounding, percentages, labels.

Conventions: pay statistics use annual base pay in USD; payroll cost is base +
bonus in USD; bands are compared against base pay in the band's currency.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

from app.models import BandScope
from app.schemas.analytics import (
    AnalyticsFilter,
    BandCompliance,
    BandComplianceQuery,
    BandPosition,
    BandRef,
    Breakdown,
    BreakdownQuery,
    BreakdownRow,
    CompaBucket,
    CompaRatioDistribution,
    CompaRatioQuery,
    CompaRatioRow,
    CompaStatsRow,
    Dimension,
    GroupKey,
    OutOfBandEmployee,
    OutOfBandFilter,
    OutOfBandRow,
    PayAssessment,
    PayStatsRow,
    PaySummary,
    SalaryStats,
)
from app.schemas.common import Page
from app.utils.currency import to_money
from app.utils.pagination import PageParams

RATIO = Decimal("0.0001")
PERCENT = Decimal("0.01")

# Compa-ratio histogram: lower bound inclusive, upper exclusive, None = unbounded.
# A symmetric band of mid -/+ 20% spans 0.80-1.20, so the edges mark "outside".
COMPA_BUCKETS: tuple[tuple[Decimal | None, Decimal | None], ...] = (
    (None, Decimal("0.80")),
    (Decimal("0.80"), Decimal("0.90")),
    (Decimal("0.90"), Decimal("1.00")),
    (Decimal("1.00"), Decimal("1.10")),
    (Decimal("1.10"), Decimal("1.20")),
    (Decimal("1.20"), None),
)


# Per-employee rules


def band_position(salary: Decimal, minimum: Decimal, maximum: Decimal) -> BandPosition:
    """Inclusive band: pay exactly at min or max is within it."""
    if salary < minimum:
        return BandPosition.BELOW
    if salary > maximum:
        return BandPosition.ABOVE
    return BandPosition.WITHIN


def compa_ratio(salary: Decimal, mid: Decimal) -> Decimal:
    """Salary / band mid, to 4 dp. 1.0000 means paid exactly at the midpoint."""
    if mid <= 0:
        raise ValueError("band mid must be positive")
    return (salary / mid).quantize(RATIO, rounding=ROUND_HALF_UP)


def band_gap(salary: Decimal, minimum: Decimal, maximum: Decimal) -> tuple[Decimal, Decimal]:
    """(amount, percent) outside the band, measured from the breached boundary."""
    position = band_position(salary, minimum, maximum)
    if position is BandPosition.BELOW:
        gap, boundary = minimum - salary, minimum
    elif position is BandPosition.ABOVE:
        gap, boundary = salary - maximum, maximum
    else:
        return Decimal("0.00"), Decimal("0.00")
    return to_money(gap), (gap / boundary * 100).quantize(PERCENT, rounding=ROUND_HALF_UP)


def salary_in_band_currency(
    *,
    base_amount: Decimal,
    base_amount_usd: Decimal,
    salary_currency: str,
    band_currency: str,
    band_rate_to_usd: Decimal,
) -> Decimal:
    """Base pay expressed in the band's currency.

    Same currency: the local amount, exactly. Otherwise (a department-wide USD
    band) the USD amount converted at the snapshot rate, rounded to cents.
    """
    if band_currency == salary_currency:
        return base_amount
    return to_money(base_amount_usd / band_rate_to_usd)


def assess(salary: Decimal, band: BandRef) -> PayAssessment:
    gap_amount, gap_pct = band_gap(salary, band.min_amount, band.max_amount)
    return PayAssessment(
        band=band,
        salary_in_band_currency=salary,
        compa_ratio=compa_ratio(salary, band.mid_amount),
        position=band_position(salary, band.min_amount, band.max_amount),
        gap_amount=gap_amount,
        gap_pct=gap_pct,
    )


def percent(part: Decimal | int, whole: Decimal | int) -> Decimal | None:
    if not whole:
        return None
    return (Decimal(part) / Decimal(whole) * 100).quantize(PERCENT, rounding=ROUND_HALF_UP)


def bucket_label(lower: Decimal | None, upper: Decimal | None) -> str:
    if lower is None:
        return f"< {upper:.2f}"
    if upper is None:
        return f">= {lower:.2f}"
    return f"{lower:.2f}-{upper:.2f}"


# Assembly


class AnalyticsRepositoryPort(Protocol):
    def pay_stats(self, by: Dimension | None, filters: AnalyticsFilter) -> list[PayStatsRow]: ...

    def compa_stats(
        self,
        by: Dimension | None,
        filters: AnalyticsFilter,
        buckets: tuple[tuple[Decimal | None, Decimal | None], ...],
    ) -> list[CompaStatsRow]: ...

    def out_of_band(
        self, filters: AnalyticsFilter, position: OutOfBandFilter, page: PageParams
    ) -> tuple[list[OutOfBandRow], int]: ...

    def fx_as_of(self) -> date | None: ...


def _money(value: Decimal | None) -> Decimal | None:
    return None if value is None else to_money(value)


def _ratio(value: Decimal | None) -> Decimal | None:
    return None if value is None else value.quantize(RATIO, rounding=ROUND_HALF_UP)


def _salary_stats(row: PayStatsRow) -> SalaryStats:
    return SalaryStats(
        avg=_money(row.avg_base_usd),
        median=_money(row.median_base_usd),
        min=_money(row.min_base_usd),
        max=_money(row.max_base_usd),
    )


def _compliance(row: PayStatsRow) -> BandCompliance:
    with_band = row.below_band + row.within_band + row.above_band
    return BandCompliance(
        below=row.below_band,
        within=row.within_band,
        above=row.above_band,
        no_band=row.no_band,
        compliance_pct=percent(row.within_band, with_band),
    )


_EMPTY = PayStatsRow(
    key=None,
    name="All",
    headcount=0,
    payroll_cost_usd=Decimal("0"),
    avg_base_usd=None,
    median_base_usd=None,
    min_base_usd=None,
    max_base_usd=None,
    below_band=0,
    within_band=0,
    above_band=0,
    no_band=0,
)


class AnalyticsService:
    def __init__(self, analytics: AnalyticsRepositoryPort) -> None:
        self._analytics = analytics

    def summary(self, filters: AnalyticsFilter) -> PaySummary:
        pay = next(iter(self._analytics.pay_stats(None, filters)), _EMPTY)
        compa = next(iter(self._analytics.compa_stats(None, filters, COMPA_BUCKETS)), None)
        return PaySummary(
            headcount=pay.headcount,
            payroll_cost_usd=to_money(pay.payroll_cost_usd),
            base_salary_usd=_salary_stats(pay),
            band_compliance=_compliance(pay),
            compa_ratio_median=_ratio(compa.median) if compa else None,
            fx_as_of=self._analytics.fx_as_of(),
        )

    def breakdown(self, query: BreakdownQuery) -> Breakdown:
        rows = self._analytics.pay_stats(query.by, query)
        total_payroll = sum((r.payroll_cost_usd for r in rows), Decimal("0"))
        return Breakdown(
            by=query.by,
            rows=[
                BreakdownRow(
                    group=GroupKey(id=r.key, name=r.name),
                    headcount=r.headcount,
                    payroll_cost_usd=to_money(r.payroll_cost_usd),
                    payroll_share_pct=percent(r.payroll_cost_usd, total_payroll),
                    base_salary_usd=_salary_stats(r),
                    band_compliance=_compliance(r),
                )
                for r in rows
            ],
        )

    def compa_ratio_distribution(self, query: CompaRatioQuery) -> CompaRatioDistribution:
        rows = self._analytics.compa_stats(query.by, query, COMPA_BUCKETS)
        return CompaRatioDistribution(
            by=query.by,
            rows=[
                CompaRatioRow(
                    group=GroupKey(id=r.key, name=r.name),
                    employees_with_band=r.employees_with_band,
                    avg=_ratio(r.avg),
                    p25=_ratio(r.p25),
                    median=_ratio(r.median),
                    p75=_ratio(r.p75),
                    min=_ratio(r.min),
                    max=_ratio(r.max),
                    buckets=[
                        CompaBucket(
                            label=bucket_label(lower, upper), lower=lower, upper=upper, count=n
                        )
                        for (lower, upper), n in zip(COMPA_BUCKETS, r.bucket_counts, strict=True)
                    ],
                )
                for r in rows
            ],
        )

    def band_compliance(self, query: BandComplianceQuery) -> Page[OutOfBandEmployee]:
        rows, total = self._analytics.out_of_band(query.filters, query.position, query.page_params)
        return Page(
            items=[_out_of_band_employee(r) for r in rows],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )


def _out_of_band_employee(row: OutOfBandRow) -> OutOfBandEmployee:
    band = BandRef(
        id=row.band_id,
        scope=BandScope(row.band_scope),
        currency_code=row.band_currency_code,
        min_amount=row.band_min,
        mid_amount=row.band_mid,
        max_amount=row.band_max,
    )
    return OutOfBandEmployee(
        employee_id=row.employee_id,
        employee_code=row.employee_code,
        full_name=f"{row.first_name} {row.last_name}",
        department=row.department,
        role=row.role,
        level=row.level,
        country_code=row.country_code,
        currency_code=row.currency_code,
        base_amount=row.base_amount,
        assessment=assess(row.salary_in_band_currency, band),
    )
