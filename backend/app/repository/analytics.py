"""Analytics SQL: hand-written aggregates over the current workforce, CQRS-lite.

Every query starts from one CTE, the *population*: one row per employee who is
not terminated, with their current pay and the band that applies to them today.
The band is resolved in SQL with the same fallback chain as BandResolver
(exact -> department+level+country -> department+level): three outer joins, each
a probe of the unique band-scope index, coalesced in that order.

Medians and percentiles use ROW_NUMBER() windows with linear interpolation
between the two nearest ranks (the PERCENTILE_CONT definition; MySQL has no
built-in). Nothing is aggregated in Python.
"""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CTE,
    ColumnElement,
    Numeric,
    and_,
    case,
    cast,
    func,
    literal,
    select,
)
from sqlalchemy.orm import Session, aliased

from app.models import (
    BandScope,
    Country,
    Department,
    Employee,
    EmployeeStatus,
    FxRate,
    JobRole,
    Level,
    SalaryBand,
    SalaryRecord,
)
from app.schemas.analytics import (
    AnalyticsFilter,
    BandPosition,
    CompaStatsRow,
    Dimension,
    OutOfBandFilter,
    OutOfBandRow,
    PayStatsRow,
)
from app.utils.pagination import PageParams

Buckets = tuple[tuple[Decimal | None, Decimal | None], ...]

# Dimension -> (population column, reference table, display column)
_DIMENSIONS: dict[Dimension, tuple[str, Any, Any]] = {
    Dimension.DEPARTMENT: ("department_id", Department, Department.name),
    Dimension.COUNTRY: ("country_id", Country, Country.name),
    Dimension.LEVEL: ("level_id", Level, Level.code),
    Dimension.ROLE: ("role_id", JobRole, JobRole.name),
}
_DIMENSION_ORDER = {
    Dimension.DEPARTMENT: Department.name,
    Dimension.COUNTRY: Country.name,
    Dimension.LEVEL: Level.rank,
    Dimension.ROLE: JobRole.name,
}
_ALL = "All"


def _population(filters: AnalyticsFilter) -> CTE:
    exact = aliased(SalaryBand, name="band_exact")
    dept_country = aliased(SalaryBand, name="band_dept_country")
    dept = aliased(SalaryBand, name="band_dept")
    band_fx = aliased(FxRate, name="band_fx")

    def band(column: str) -> ColumnElement:
        return func.coalesce(
            getattr(exact, column), getattr(dept_country, column), getattr(dept, column)
        )

    band_id = band("id")
    band_currency = band("currency_code")
    band_min, band_mid, band_max = band("min_amount"), band("mid_amount"), band("max_amount")
    # Same rule as services.analytics.salary_in_band_currency.
    salary_in_band = case(
        (band_currency == SalaryRecord.currency_code, SalaryRecord.base_amount),
        else_=func.round(SalaryRecord.base_amount_usd / band_fx.rate_to_usd, 2),
    )
    # Same rule as services.analytics.band_position: min and max are inside the band.
    position = case(
        (band_id.is_(None), BandPosition.NO_BAND.value),
        (salary_in_band < band_min, BandPosition.BELOW.value),
        (salary_in_band > band_max, BandPosition.ABOVE.value),
        else_=BandPosition.WITHIN.value,
    )
    scope = case(
        (exact.id.is_not(None), BandScope.EXACT.value),
        (dept_country.id.is_not(None), BandScope.DEPARTMENT_LEVEL_COUNTRY.value),
        (dept.id.is_not(None), BandScope.DEPARTMENT_LEVEL.value),
    )

    conditions = [Employee.status != EmployeeStatus.TERMINATED]
    for column, value in (
        (Employee.department_id, filters.department_id),
        (Employee.role_id, filters.role_id),
        (Employee.level_id, filters.level_id),
        (Employee.country_id, filters.country_id),
    ):
        if value is not None:
            conditions.append(column == value)

    def band_join(alias: Any, role: ColumnElement, country: ColumnElement) -> ColumnElement:
        return and_(
            alias.department_id == Employee.department_id,
            alias.level_id == Employee.level_id,
            alias.role_key == role,
            alias.country_key == country,
        )

    return (
        select(
            Employee.id.label("employee_id"),
            Employee.department_id,
            Employee.country_id,
            Employee.level_id,
            Employee.role_id,
            SalaryRecord.currency_code,
            SalaryRecord.base_amount,
            SalaryRecord.base_amount_usd.label("base_usd"),
            (SalaryRecord.base_amount_usd + SalaryRecord.bonus_amount_usd).label("total_usd"),
            band_id.label("band_id"),
            scope.label("band_scope"),
            band_currency.label("band_currency_code"),
            band_min.label("band_min"),
            band_mid.label("band_mid"),
            band_max.label("band_max"),
            salary_in_band.label("salary_in_band"),
            (salary_in_band / band_mid).label("compa"),
            position.label("position"),
        )
        .select_from(Employee)
        .join(SalaryRecord, SalaryRecord.current_employee_id == Employee.id)
        .outerjoin(exact, band_join(exact, Employee.role_id, Employee.country_id))
        .outerjoin(dept_country, band_join(dept_country, literal(0), Employee.country_id))
        .outerjoin(dept, band_join(dept, literal(0), literal(0)))
        .outerjoin(band_fx, band_fx.currency_code == band_currency)
        .where(*conditions)
        .cte("population")
    )


def _group_key(population: CTE, by: Dimension | None) -> tuple[ColumnElement, Any]:
    """(key column, PARTITION BY clause). The whole population is one unpartitioned group."""
    if by is None:
        return literal(0), None
    column = population.c[_DIMENSIONS[by][0]]
    return column, column


def _percentile(
    value: ColumnElement, rank: ColumnElement, count: ColumnElement, p: Decimal
) -> ColumnElement:
    """Linear-interpolated percentile over ranked rows; use with GROUP BY key, count.

    position = 1 + (n - 1) * p; interpolate between the rows ranked floor/ceil of it.
    NULL when the group has no values (n = 0).
    """
    position = 1 + (count - 1) * cast(literal(p), Numeric(6, 4))
    lower_rank, upper_rank = func.floor(position), func.ceil(position)
    lower = func.max(case((rank == lower_rank, value)))
    upper = func.max(case((rank == upper_rank, value)))
    return lower + (upper - lower) * (position - lower_rank)


def _count_where(condition: ColumnElement[bool]) -> ColumnElement:
    return func.coalesce(func.sum(case((condition, 1), else_=0)), 0)


class AnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def pay_stats(self, by: Dimension | None, filters: AnalyticsFilter) -> list[PayStatsRow]:
        population = _population(filters)
        key, partition = _group_key(population, by)
        ranked = select(
            key.label("key"),
            population.c.base_usd,
            population.c.total_usd,
            population.c.position,
            func.row_number()
            .over(partition_by=partition, order_by=population.c.base_usd)
            .label("rn"),
            func.count().over(partition_by=partition).label("n"),
        ).cte("ranked")
        r = ranked.c
        stmt = select(
            r.key,
            r.n,
            func.sum(r.total_usd),
            func.avg(r.base_usd),
            _percentile(r.base_usd, r.rn, r.n, Decimal("0.5")),
            func.min(r.base_usd),
            func.max(r.base_usd),
            _count_where(r.position == BandPosition.BELOW.value),
            _count_where(r.position == BandPosition.WITHIN.value),
            _count_where(r.position == BandPosition.ABOVE.value),
            _count_where(r.position == BandPosition.NO_BAND.value),
        ).group_by(r.key, r.n)

        rows = {row[0]: row for row in self.session.execute(stmt)}
        return [
            PayStatsRow(
                key=key_id,
                name=name,
                headcount=row[1],
                payroll_cost_usd=row[2],
                avg_base_usd=row[3],
                median_base_usd=row[4],
                min_base_usd=row[5],
                max_base_usd=row[6],
                below_band=int(row[7]),
                within_band=int(row[8]),
                above_band=int(row[9]),
                no_band=int(row[10]),
            )
            for key_id, name, row in self._named(by, rows)
        ]

    def compa_stats(
        self, by: Dimension | None, filters: AnalyticsFilter, buckets: Buckets
    ) -> list[CompaStatsRow]:
        population = _population(filters)
        key, partition = _group_key(population, by)
        compa = population.c.compa
        ranked = select(
            key.label("key"),
            compa.label("compa"),
            # employees without a band have no compa-ratio: rank them after everyone else
            func.row_number()
            .over(partition_by=partition, order_by=[compa.is_(None), compa])
            .label("rn"),
            func.count(compa).over(partition_by=partition).label("n"),
        ).cte("ranked")
        r = ranked.c

        def in_bucket(lower: Decimal | None, upper: Decimal | None) -> ColumnElement[bool]:
            bounds = [r.compa.is_not(None)]
            if lower is not None:
                bounds.append(r.compa >= lower)
            if upper is not None:
                bounds.append(r.compa < upper)
            return and_(*bounds)

        stmt = select(
            r.key,
            r.n,
            func.avg(r.compa),
            _percentile(r.compa, r.rn, r.n, Decimal("0.25")),
            _percentile(r.compa, r.rn, r.n, Decimal("0.5")),
            _percentile(r.compa, r.rn, r.n, Decimal("0.75")),
            func.min(r.compa),
            func.max(r.compa),
            *(_count_where(in_bucket(lower, upper)) for lower, upper in buckets),
        ).group_by(r.key, r.n)

        rows = {row[0]: row for row in self.session.execute(stmt)}
        return [
            CompaStatsRow(
                key=key_id,
                name=name,
                employees_with_band=row[1],
                avg=row[2],
                p25=row[3],
                median=row[4],
                p75=row[5],
                min=row[6],
                max=row[7],
                bucket_counts=tuple(int(n) for n in row[8:]),
            )
            for key_id, name, row in self._named(by, rows)
        ]

    def out_of_band(
        self, filters: AnalyticsFilter, position: OutOfBandFilter, page: PageParams
    ) -> tuple[list[OutOfBandRow], int]:
        population = _population(filters)
        p = population.c
        wanted = {
            OutOfBandFilter.BELOW: [BandPosition.BELOW.value],
            OutOfBandFilter.ABOVE: [BandPosition.ABOVE.value],
            OutOfBandFilter.OUTSIDE: [BandPosition.BELOW.value, BandPosition.ABOVE.value],
        }[position]
        condition = p.position.in_(wanted)

        total = self.session.scalar(select(func.count()).select_from(population).where(condition))
        # Most severe first: distance from the breached boundary, relative to it.
        severity = case(
            (p.position == BandPosition.BELOW.value, (p.band_min - p.salary_in_band) / p.band_min),
            else_=(p.salary_in_band - p.band_max) / p.band_max,
        )
        stmt = (
            select(
                p.employee_id,
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
                Department.name,
                JobRole.name,
                Level.code,
                Country.code,
                p.currency_code,
                p.base_amount,
                p.band_id,
                p.band_scope,
                p.band_currency_code,
                p.band_min,
                p.band_mid,
                p.band_max,
                p.salary_in_band,
            )
            .select_from(population)
            .join(Employee, Employee.id == p.employee_id)
            .join(Department, Department.id == p.department_id)
            .join(JobRole, JobRole.id == p.role_id)
            .join(Level, Level.id == p.level_id)
            .join(Country, Country.id == p.country_id)
            .where(condition)
            .order_by(severity.desc(), p.employee_id)
            .limit(page.limit)
            .offset(page.offset)
        )
        return [OutOfBandRow(*row) for row in self.session.execute(stmt)], total or 0

    def fx_as_of(self) -> date | None:
        return self.session.scalar(select(func.max(FxRate.as_of)))

    def _named(self, by: Dimension | None, rows: dict[Any, Any]):
        """Attach display names and order groups the way HR reads them (levels by rank)."""
        if by is None:
            for row in rows.values():
                yield None, _ALL, row
            return
        _, table, name_column = _DIMENSIONS[by]
        names = self.session.execute(
            select(table.id, name_column).order_by(_DIMENSION_ORDER[by])
        ).all()
        for key_id, name in names:
            if key_id in rows:
                yield key_id, name, rows[key_id]
