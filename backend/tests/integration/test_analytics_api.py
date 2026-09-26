"""Analytics SQL checked against an independent Python oracle on generated data."""

import statistics
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, update
from sqlalchemy.orm import Session

from app.models import JobRole, SalaryRecord
from app.seed.generator import SeedData, generate
from app.seed.seed import LOAD_ORDER

URL = "/api/v1/analytics"
CENT, RATIO = Decimal("0.01"), Decimal("0.0001")


@pytest.fixture
def data(db_session: Session) -> SeedData:
    data = generate(seed=5, employee_count=300)
    for model, attr in LOAD_ORDER:
        db_session.execute(insert(model.__table__), getattr(data, attr))
    db_session.flush()
    return data


class Oracle:
    """The same figures, computed row by row in Python from the generated data."""

    def __init__(self, data: SeedData) -> None:
        bands = {
            (b["department_id"], b["role_id"], b["level_id"], b["country_id"]): b
            for b in data.salary_bands
        }
        current = {r["employee_id"]: r for r in data.salary_records if r["is_current"]}
        self.rows = []
        for emp in data.employees:
            if emp["status"] == "terminated":
                continue
            pay = current[emp["id"]]
            band = bands[(emp["department_id"], emp["role_id"], emp["level_id"], emp["country_id"])]
            base = pay["base_amount"]  # seeded bands are in the salary currency
            position = (
                "below"
                if base < band["min_amount"]
                else "above"
                if base > band["max_amount"]
                else "within"
            )
            self.rows.append(
                {
                    **emp,
                    "base_usd": pay["base_amount_usd"],
                    "total_usd": pay["base_amount_usd"] + pay["bonus_amount_usd"],
                    "compa": base / band["mid_amount"],
                    "position": position,
                }
            )

    def by(self, key: str) -> dict[int, list[dict]]:
        groups: dict[int, list[dict]] = defaultdict(list)
        for row in self.rows:
            groups[row[key]].append(row)
        return groups


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _close(api_value: str, expected: Decimal) -> bool:
    # MySQL keeps 6 dp on DECIMAL division before we round to 4; allow one unit.
    return abs(Decimal(api_value) - expected.quantize(RATIO, rounding=ROUND_HALF_UP)) <= RATIO


def test_summary_matches_the_oracle(client: TestClient, data: SeedData) -> None:
    oracle = Oracle(data)
    base = [r["base_usd"] for r in oracle.rows]

    body = client.get(f"{URL}/summary").json()

    assert body["headcount"] == len(oracle.rows)
    assert Decimal(body["payroll_cost_usd"]) == sum(r["total_usd"] for r in oracle.rows)
    stats = body["base_salary_usd"]
    assert Decimal(stats["median"]) == _cents(statistics.median(base))
    assert Decimal(stats["avg"]) == _cents(sum(base) / len(base))
    assert Decimal(stats["min"]) == min(base)
    assert Decimal(stats["max"]) == max(base)
    positions = [r["position"] for r in oracle.rows]
    compliance = body["band_compliance"]
    assert compliance["below"] == positions.count("below") > 0
    assert compliance["above"] == positions.count("above") > 0
    assert compliance["within"] == positions.count("within")
    assert compliance["no_band"] == 0
    assert _close(body["compa_ratio_median"], statistics.median(r["compa"] for r in oracle.rows))
    assert body["fx_as_of"] == "2026-09-01"


@pytest.mark.parametrize(
    ("by", "key"),
    [("department", "department_id"), ("country", "country_id"), ("level", "level_id")],
)
def test_breakdown_matches_the_oracle_per_group(
    client: TestClient, data: SeedData, by: str, key: str
) -> None:
    groups = Oracle(data).by(key)

    body = client.get(f"{URL}/breakdown", params={"by": by}).json()

    assert {row["group"]["id"] for row in body["rows"]} == set(groups)
    for row in body["rows"]:
        members = groups[row["group"]["id"]]
        base = [m["base_usd"] for m in members]
        assert row["headcount"] == len(members)
        assert Decimal(row["payroll_cost_usd"]) == sum(m["total_usd"] for m in members)
        assert Decimal(row["base_salary_usd"]["median"]) == _cents(statistics.median(base))
        assert row["band_compliance"]["below"] == sum(m["position"] == "below" for m in members)
    shares = sum(Decimal(row["payroll_share_pct"]) for row in body["rows"])
    assert abs(shares - 100) <= Decimal("0.05")
    if by == "level":
        assert [row["group"]["name"] for row in body["rows"]] == ["L1", "L2", "L3", "L4", "L5"]


def test_compa_ratio_quartiles_and_histogram_match_the_oracle(
    client: TestClient, data: SeedData
) -> None:
    groups = Oracle(data).by("department_id")

    body = client.get(f"{URL}/compa-ratio", params={"by": "department"}).json()

    for row in body["rows"]:
        compa = sorted(m["compa"] for m in groups[row["group"]["id"]])
        p25, p50, p75 = statistics.quantiles(compa, n=4, method="inclusive")
        assert row["employees_with_band"] == len(compa)
        assert _close(row["p25"], p25)
        assert _close(row["median"], p50)
        assert _close(row["p75"], p75)
        assert _close(row["min"], compa[0])
        assert _close(row["max"], compa[-1])
        assert sum(b["count"] for b in row["buckets"]) == len(compa)
        assert row["buckets"][0]["count"] == sum(c < Decimal("0.8") for c in compa)
        assert row["buckets"][-1]["count"] == sum(c >= Decimal("1.2") for c in compa)


def test_band_compliance_lists_everyone_outside_most_severe_first(
    client: TestClient, data: SeedData
) -> None:
    oracle = Oracle(data)
    outside = {r["id"] for r in oracle.rows if r["position"] != "within"}

    body = client.get(f"{URL}/band-compliance", params={"page_size": 200}).json()

    assert body["total"] == len(outside)
    assert {i["employee_id"] for i in body["items"]} == outside
    gaps = [Decimal(i["assessment"]["gap_pct"]) for i in body["items"]]
    assert gaps == sorted(gaps, reverse=True)
    below = client.get(f"{URL}/band-compliance", params={"position": "below"}).json()
    assert {i["assessment"]["position"] for i in below["items"]} == {"below"}


def test_filters_narrow_the_population(client: TestClient, data: SeedData) -> None:
    rows = Oracle(data).by("country_id")
    country_id = max(rows, key=lambda k: len(rows[k]))

    body = client.get(f"{URL}/summary", params={"country_id": country_id}).json()

    assert body["headcount"] == len(rows[country_id])


def test_band_boundaries_are_inclusive_in_sql(
    client: TestClient, db_session: Session, data: SeedData
) -> None:
    """Pay exactly at min is within the band; one cent below is not."""
    emp = next(r for r in Oracle(data).rows if r["position"] == "within")
    band = next(
        b
        for b in data.salary_bands
        if (b["department_id"], b["role_id"], b["level_id"], b["country_id"])
        == (emp["department_id"], emp["role_id"], emp["level_id"], emp["country_id"])
    )

    def set_base(amount: Decimal) -> list[int]:
        db_session.execute(
            update(SalaryRecord)
            .where(SalaryRecord.current_employee_id == emp["id"])
            .values(base_amount=amount)
        )
        body = client.get(f"{URL}/band-compliance", params={"page_size": 200}).json()
        return [i["employee_id"] for i in body["items"]]

    assert emp["id"] not in set_base(band["min_amount"])
    assert emp["id"] not in set_base(band["max_amount"])
    assert emp["id"] in set_base(band["min_amount"] - Decimal("0.01"))
    assert emp["id"] in set_base(band["max_amount"] + Decimal("0.01"))


def test_band_is_resolved_from_todays_placement(client: TestClient, data: SeedData) -> None:
    """A promotion without a pay rise shows up as below the new level's band."""
    emp = next(r for r in Oracle(data).rows if r["position"] == "within" and r["level_id"] == 1)

    client.patch(f"/api/v1/employees/{emp['id']}", json={"level_id": 5})

    body = client.get(f"{URL}/band-compliance", params={"position": "below", "page_size": 200})
    item = next(i for i in body.json()["items"] if i["employee_id"] == emp["id"])
    assert item["level"] == "L5"
    detail = client.get(f"/api/v1/employees/{emp['id']}").json()
    assert detail["pay_assessment"]["position"] == "below"
    assert detail["pay_assessment"]["band"]["id"] == item["assessment"]["band"]["id"]


def test_fallback_usd_band_applies_when_no_specific_band_exists(
    client: TestClient, db_session: Session, data: SeedData
) -> None:
    dept_id = data.departments[0]["id"]
    role = JobRole(department_id=dept_id, name="Brand New Role")
    db_session.add(role)
    db_session.flush()
    hire = client.post(
        "/api/v1/employees",
        json={
            "employee_code": "N00001",
            "first_name": "New",
            "last_name": "Hire",
            "email": "new.hire@acme.example",
            "department_id": dept_id,
            "role_id": role.id,
            "level_id": 1,
            "country_id": 2,  # India, INR
            "hire_date": "2026-08-01",
            "base_amount": "500000.00",  # 5950.00 USD at the snapshot rate
        },
    ).json()
    before = client.get(f"{URL}/summary").json()["band_compliance"]["no_band"]
    assert before == 1
    assert hire["pay_assessment"] is None

    client.post(
        "/api/v1/bands",
        json={
            "department_id": dept_id,
            "level_id": 1,
            "min_amount": "10000.00",
            "mid_amount": "12000.00",
            "max_amount": "14000.00",
        },
    )

    assert client.get(f"{URL}/summary").json()["band_compliance"]["no_band"] == 0
    items = client.get(
        f"{URL}/band-compliance", params={"position": "below", "page_size": 200}
    ).json()["items"]
    item = next(i for i in items if i["employee_id"] == hire["id"])
    assert item["assessment"]["band"]["scope"] == "department+level"
    assert item["assessment"]["band"]["currency_code"] == "USD"
    assert item["assessment"]["salary_in_band_currency"] == "5950.00"
    assert item["assessment"]["compa_ratio"] == "0.4958"
    detail = client.get(f"/api/v1/employees/{hire['id']}").json()
    assert detail["pay_assessment"] == item["assessment"]
