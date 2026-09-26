from datetime import date
from decimal import Decimal

import pytest

from app.models import BandScope
from app.schemas.analytics import (
    AnalyticsFilter,
    BandComplianceQuery,
    BandPosition,
    BandRef,
    BreakdownQuery,
    CompaRatioQuery,
    CompaStatsRow,
    Dimension,
    OutOfBandFilter,
    OutOfBandRow,
    PayStatsRow,
)
from app.services.analytics import (
    COMPA_BUCKETS,
    AnalyticsService,
    assess,
    band_gap,
    band_position,
    bucket_label,
    compa_ratio,
    percent,
    salary_in_band_currency,
)
from app.utils.pagination import PageParams

D = Decimal
MIN, MID, MAX = D("80000.00"), D("100000.00"), D("120000.00")


class TestBandPosition:
    @pytest.mark.parametrize(
        ("salary", "position"),
        [
            (D("79999.99"), BandPosition.BELOW),
            (D("80000.00"), BandPosition.WITHIN),  # exactly at min: inside
            (D("100000.00"), BandPosition.WITHIN),
            (D("120000.00"), BandPosition.WITHIN),  # exactly at max: inside
            (D("120000.01"), BandPosition.ABOVE),
        ],
    )
    def test_boundaries_are_inclusive(self, salary: Decimal, position: BandPosition) -> None:
        assert band_position(salary, MIN, MAX) is position

    def test_flat_band(self) -> None:
        assert band_position(D("100"), D("100"), D("100")) is BandPosition.WITHIN


class TestCompaRatio:
    @pytest.mark.parametrize(
        ("salary", "expected"),
        [
            (MID, D("1.0000")),
            (MIN, D("0.8000")),
            (MAX, D("1.2000")),
            (D("100000.00") / 3, D("0.3333")),
            (D("66666.67"), D("0.6667")),
            (D("100005.00"), D("1.0001")),  # 1.00005 rounds half up
        ],
    )
    def test_ratio_to_mid_at_four_places(self, salary: Decimal, expected: Decimal) -> None:
        assert compa_ratio(salary, MID) == expected

    def test_non_positive_mid_is_an_error(self) -> None:
        with pytest.raises(ValueError):
            compa_ratio(D("1"), D("0"))


class TestBandGap:
    def test_inside_the_band_has_no_gap(self) -> None:
        assert band_gap(MIN, MIN, MAX) == (D("0.00"), D("0.00"))
        assert band_gap(MAX, MIN, MAX) == (D("0.00"), D("0.00"))

    def test_below_is_measured_from_min(self) -> None:
        assert band_gap(D("72000.00"), MIN, MAX) == (D("8000.00"), D("10.00"))

    def test_above_is_measured_from_max(self) -> None:
        assert band_gap(D("150000.00"), MIN, MAX) == (D("30000.00"), D("25.00"))

    def test_one_cent_outside(self) -> None:
        assert band_gap(D("79999.99"), MIN, MAX) == (D("0.01"), D("0.00"))


class TestSalaryInBandCurrency:
    def test_same_currency_uses_the_local_amount_exactly(self) -> None:
        salary = salary_in_band_currency(
            base_amount=D("1500000.00"),
            base_amount_usd=D("17850.00"),
            salary_currency="INR",
            band_currency="INR",
            band_rate_to_usd=D("0.01190000"),
        )
        assert salary == D("1500000.00")

    def test_usd_band_uses_the_usd_amount(self) -> None:
        salary = salary_in_band_currency(
            base_amount=D("1500000.00"),
            base_amount_usd=D("17850.00"),
            salary_currency="INR",
            band_currency="USD",
            band_rate_to_usd=D("1.00000000"),
        )
        assert salary == D("17850.00")

    def test_other_currency_converts_through_usd_to_cents(self) -> None:
        salary = salary_in_band_currency(
            base_amount=D("1000.00"),
            base_amount_usd=D("1000.00"),
            salary_currency="USD",
            band_currency="GBP",
            band_rate_to_usd=D("1.27000000"),
        )
        assert salary == D("787.40")  # 787.4015...


def test_assess_combines_position_compa_and_gap() -> None:
    band = BandRef(
        id=7,
        scope=BandScope.EXACT,
        currency_code="USD",
        min_amount=MIN,
        mid_amount=MID,
        max_amount=MAX,
    )

    result = assess(D("60000.00"), band)

    assert result.position is BandPosition.BELOW
    assert result.compa_ratio == D("0.6000")
    assert result.gap_amount == D("20000.00")
    assert result.gap_pct == D("25.00")
    assert result.band == band


def test_percent_of_zero_is_undefined() -> None:
    assert percent(3, 0) is None
    assert percent(1, 3) == D("33.33")
    assert percent(2, 3) == D("66.67")


def test_compa_buckets_are_contiguous_and_unbounded_at_the_ends() -> None:
    assert COMPA_BUCKETS[0][0] is None
    assert COMPA_BUCKETS[-1][1] is None
    for (_, upper), (lower, _) in zip(COMPA_BUCKETS, COMPA_BUCKETS[1:], strict=False):
        assert upper == lower
    assert [bucket_label(lo, hi) for lo, hi in COMPA_BUCKETS] == [
        "< 0.80",
        "0.80-0.90",
        "0.90-1.00",
        "1.00-1.10",
        "1.10-1.20",
        ">= 1.20",
    ]


# Assembly on fixed fixtures


def _pay_row(key: int | None, name: str, **values: object) -> PayStatsRow:
    fields: dict[str, object] = {
        "headcount": 10,
        "payroll_cost_usd": D("1000000"),
        "avg_base_usd": D("91234.567891"),
        "median_base_usd": D("90000.005"),
        "min_base_usd": D("50000.00"),
        "max_base_usd": D("150000.00"),
        "below_band": 1,
        "within_band": 8,
        "above_band": 1,
        "no_band": 0,
    }
    fields.update(values)
    return PayStatsRow(key=key, name=name, **fields)  # type: ignore[arg-type]


def _compa_row(key: int | None, name: str, **values: object) -> CompaStatsRow:
    fields: dict[str, object] = {
        "employees_with_band": 6,
        "avg": D("1.004166667"),
        "p25": D("0.9125"),
        "median": D("1.00005"),
        "p75": D("1.1"),
        "min": D("0.75"),
        "max": D("1.25"),
        "bucket_counts": (1, 0, 2, 1, 1, 1),
    }
    fields.update(values)
    return CompaStatsRow(key=key, name=name, **fields)  # type: ignore[arg-type]


class FakeAnalyticsRepository:
    def __init__(self) -> None:
        self.pay: dict[Dimension | None, list[PayStatsRow]] = {}
        self.compa: dict[Dimension | None, list[CompaStatsRow]] = {}
        self.out_of_band_rows: list[OutOfBandRow] = []
        self.calls: list[tuple] = []

    def pay_stats(self, by, filters):
        self.calls.append(("pay", by, filters.department_id))
        return self.pay.get(by, [])

    def compa_stats(self, by, filters, buckets):
        assert buckets == COMPA_BUCKETS
        return self.compa.get(by, [])

    def out_of_band(self, filters, position, page):
        self.calls.append(("out_of_band", position, page, filters.country_id))
        return self.out_of_band_rows, 42

    def fx_as_of(self) -> date | None:
        return date(2026, 9, 1)


@pytest.fixture
def repo() -> FakeAnalyticsRepository:
    return FakeAnalyticsRepository()


class TestSummary:
    def test_rounds_money_and_derives_compliance(self, repo: FakeAnalyticsRepository) -> None:
        repo.pay[None] = [
            _pay_row(None, "All", below_band=2, within_band=6, above_band=1, no_band=1)
        ]
        repo.compa[None] = [_compa_row(None, "All")]

        summary = AnalyticsService(repo).summary(AnalyticsFilter(department_id=3))

        assert summary.headcount == 10
        assert summary.payroll_cost_usd == D("1000000.00")
        assert summary.base_salary_usd.avg == D("91234.57")
        assert summary.base_salary_usd.median == D("90000.01")  # half up
        compliance = summary.band_compliance
        assert (compliance.below, compliance.within, compliance.above) == (2, 6, 1)
        assert compliance.no_band == 1
        assert compliance.compliance_pct == D("66.67")  # 6 of the 9 with a band
        assert summary.compa_ratio_median == D("1.0001")
        assert summary.fx_as_of == date(2026, 9, 1)
        assert repo.calls == [("pay", None, 3)]  # filters passed through

    def test_empty_population(self, repo: FakeAnalyticsRepository) -> None:
        summary = AnalyticsService(repo).summary(AnalyticsFilter())

        assert summary.headcount == 0
        assert summary.payroll_cost_usd == D("0.00")
        assert summary.base_salary_usd.median is None
        assert summary.band_compliance.compliance_pct is None
        assert summary.compa_ratio_median is None


class TestBreakdown:
    def test_payroll_share_per_group(self, repo: FakeAnalyticsRepository) -> None:
        repo.pay[Dimension.COUNTRY] = [
            _pay_row(1, "India", payroll_cost_usd=D("500000")),
            _pay_row(2, "United States", payroll_cost_usd=D("300000")),
            _pay_row(3, "Brazil", payroll_cost_usd=D("200000")),
        ]

        result = AnalyticsService(repo).breakdown(BreakdownQuery(by=Dimension.COUNTRY))

        assert result.by is Dimension.COUNTRY
        assert [r.group.name for r in result.rows] == ["India", "United States", "Brazil"]
        assert [r.payroll_share_pct for r in result.rows] == [D("50.00"), D("30.00"), D("20.00")]

    def test_group_with_no_band_at_all(self, repo: FakeAnalyticsRepository) -> None:
        repo.pay[Dimension.ROLE] = [
            _pay_row(1, "New role", below_band=0, within_band=0, above_band=0, no_band=10)
        ]

        row = AnalyticsService(repo).breakdown(BreakdownQuery(by=Dimension.ROLE)).rows[0]

        assert row.band_compliance.compliance_pct is None
        assert row.payroll_share_pct == D("100.00")


def test_compa_distribution_labels_buckets_and_rounds(repo: FakeAnalyticsRepository) -> None:
    repo.compa[Dimension.DEPARTMENT] = [_compa_row(1, "Engineering")]

    row = AnalyticsService(repo).compa_ratio_distribution(CompaRatioQuery()).rows[0]

    assert row.group.name == "Engineering"
    assert row.avg == D("1.0042")
    assert row.median == D("1.0001")
    assert [(b.label, b.count) for b in row.buckets] == [
        ("< 0.80", 1),
        ("0.80-0.90", 0),
        ("0.90-1.00", 2),
        ("1.00-1.10", 1),
        ("1.10-1.20", 1),
        (">= 1.20", 1),
    ]


def test_band_compliance_assesses_each_row(repo: FakeAnalyticsRepository) -> None:
    repo.out_of_band_rows = [
        OutOfBandRow(
            employee_id=5,
            employee_code="E00005",
            first_name="Asha",
            last_name="Rao",
            department="Engineering",
            role="Backend Engineer",
            level="L3",
            country_code="IN",
            currency_code="INR",
            base_amount=D("1440000.00"),
            band_id=9,
            band_scope=BandScope.EXACT,
            band_currency_code="INR",
            band_min=D("1600000.00"),
            band_mid=D("2000000.00"),
            band_max=D("2400000.00"),
            salary_in_band_currency=D("1440000.00"),
        )
    ]
    query = BandComplianceQuery(position=OutOfBandFilter.BELOW, country_id=2, page=2, page_size=10)

    page = AnalyticsService(repo).band_compliance(query)

    assert page.total == 42
    employee = page.items[0]
    assert employee.full_name == "Asha Rao"
    assessment = employee.assessment
    assert assessment.position is BandPosition.BELOW
    assert assessment.compa_ratio == D("0.7200")
    assert assessment.gap_amount == D("160000.00")
    assert assessment.gap_pct == D("10.00")
    assert repo.calls == [
        ("out_of_band", OutOfBandFilter.BELOW, PageParams(page=2, page_size=10), 2)
    ]
