"""Sanity checks on the generated 10k dataset. Pure Python, no database."""

from collections import Counter, defaultdict
from decimal import Decimal

import pytest

from app.seed import reference_data as ref
from app.seed.generator import SeedData, generate
from app.utils.currency import to_usd


@pytest.fixture(scope="module")
def data() -> SeedData:
    return generate()


def test_same_seed_gives_identical_data() -> None:
    assert generate(seed=7, employee_count=300) == generate(seed=7, employee_count=300)
    assert generate(seed=7, employee_count=300) != generate(seed=8, employee_count=300)


def test_dimension_sizes_match_the_brief(data: SeedData) -> None:
    assert len(data.employees) == 10_000
    assert len(data.departments) == 8
    assert len(data.countries) == 6
    assert len(data.levels) == 5
    assert len(data.job_roles) == 30
    assert {c["currency_code"] for c in data.countries} <= set(ref.FX_RATES_TO_USD)


def test_codes_and_emails_are_unique(data: SeedData) -> None:
    assert len({e["employee_code"] for e in data.employees}) == len(data.employees)
    assert len({e["email"] for e in data.employees}) == len(data.employees)


def test_every_role_belongs_to_the_employees_department(data: SeedData) -> None:
    role_dept = {r["id"]: r["department_id"] for r in data.job_roles}
    assert all(role_dept[e["role_id"]] == e["department_id"] for e in data.employees)


def test_managers_are_more_senior_in_the_same_department_and_inserted_first(
    data: SeedData,
) -> None:
    by_id = {e["id"]: e for e in data.employees}
    for emp in data.employees:
        if emp["manager_id"] is None:
            continue
        manager = by_id[emp["manager_id"]]
        assert manager["id"] < emp["id"]  # FK-safe insert order
        assert manager["department_id"] == emp["department_id"]
        assert manager["level_id"] > emp["level_id"]


def test_bands_are_ordered_and_priced_in_the_country_currency(data: SeedData) -> None:
    currency = {c["id"]: c["currency_code"] for c in data.countries}
    for band in data.salary_bands:
        assert 0 < band["min_amount"] < band["mid_amount"] < band["max_amount"]
        assert band["currency_code"] == currency[band["country_id"]]


def test_salary_history_is_contiguous_with_exactly_one_current_record(data: SeedData) -> None:
    history: dict[int, list[dict]] = defaultdict(list)
    for record in data.salary_records:
        history[record["employee_id"]].append(record)
    hire_date = {e["id"]: e["hire_date"] for e in data.employees}

    assert history.keys() == hire_date.keys()
    for emp_id, records in history.items():
        records.sort(key=lambda r: r["effective_from"])
        assert records[0]["effective_from"] == hire_date[emp_id]
        assert records[0]["reason"] == "hire"
        assert [r["is_current"] for r in records] == [False] * (len(records) - 1) + [True]
        assert records[-1]["effective_to"] is None
        for earlier, later in zip(records, records[1:], strict=False):
            # half-open periods: each one ends exactly where the next begins
            assert earlier["effective_to"] == later["effective_from"]
            assert earlier["effective_from"] < later["effective_from"]
        assert all(r["effective_from"] <= ref.AS_OF for r in records)


def test_amounts_are_positive_and_usd_uses_the_snapshot_rate(data: SeedData) -> None:
    for record in data.salary_records:
        assert record["base_amount"] > 0
        assert record["bonus_amount"] >= 0
        assert record["fx_rate_to_usd"] == ref.FX_RATES_TO_USD[record["currency_code"]]
        assert record["base_amount_usd"] == to_usd(record["base_amount"], record["fx_rate_to_usd"])


def test_current_pay_links_the_exact_band_for_the_current_cell(data: SeedData) -> None:
    band_by_cell = {
        (b["department_id"], b["role_id"], b["level_id"], b["country_id"]): b
        for b in data.salary_bands
    }
    current = {r["employee_id"]: r for r in data.salary_records if r["is_current"]}
    for emp in data.employees:
        cell = (emp["department_id"], emp["role_id"], emp["level_id"], emp["country_id"])
        assert current[emp["id"]]["band_id"] == band_by_cell[cell]["id"]


def test_three_to_five_percent_are_paid_outside_their_band_on_both_sides(
    data: SeedData,
) -> None:
    bands = {b["id"]: b for b in data.salary_bands}
    placement: Counter[str] = Counter()
    for record in data.salary_records:
        if not record["is_current"]:
            continue
        band = bands[record["band_id"]]
        if record["base_amount"] < band["min_amount"]:
            placement["below"] += 1
        elif record["base_amount"] > band["max_amount"]:
            placement["above"] += 1

    share = Decimal(placement["below"] + placement["above"]) / len(data.employees)
    assert Decimal("0.03") <= share <= Decimal("0.05")
    assert placement["below"] > 0
    assert placement["above"] > 0
