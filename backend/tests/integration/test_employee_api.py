"""Employee endpoints against real MySQL, on a small generated dataset."""

from collections import Counter
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.seed.generator import SeedData, generate
from app.seed.seed import LOAD_ORDER

URL = "/api/v1/employees"


@pytest.fixture
def data(db_session: Session) -> SeedData:
    data = generate(seed=11, employee_count=60)
    for model, attr in LOAD_ORDER:
        db_session.execute(insert(model.__table__), getattr(data, attr))
    db_session.flush()
    return data


def _current(data: SeedData) -> dict[int, dict]:
    return {r["employee_id"]: r for r in data.salary_records if r["is_current"]}


class TestList:
    def test_first_page_sorted_by_name_with_total(self, client: TestClient, data: SeedData) -> None:
        body = client.get(URL, params={"page_size": 25}).json()

        assert body["total"] == 60
        assert len(body["items"]) == 25
        names = [(i["last_name"], i["first_name"]) for i in body["items"]]
        assert names == sorted(names, key=lambda n: (n[0].lower(), n[1].lower()))

    def test_pages_do_not_overlap(self, client: TestClient, data: SeedData) -> None:
        first = client.get(URL, params={"page_size": 20, "page": 1}).json()["items"]
        second = client.get(URL, params={"page_size": 20, "page": 2}).json()["items"]
        third = client.get(URL, params={"page_size": 20, "page": 3}).json()["items"]

        ids = [i["id"] for i in first + second + third]
        assert len(ids) == len(set(ids)) == 60

    def test_row_carries_names_and_current_pay(self, client: TestClient, data: SeedData) -> None:
        item = client.get(URL, params={"q": "E00001"}).json()["items"][0]
        current = _current(data)[1]

        assert item["employee_code"] == "E00001"
        assert item["department"] and item["role"] and item["level"].startswith("L")
        assert item["currency_code"] == current["currency_code"]
        assert Decimal(item["base_amount"]) == current["base_amount"]
        assert Decimal(item["base_amount_usd"]) == current["base_amount_usd"]

    def test_filters_combine(self, client: TestClient, data: SeedData) -> None:
        dept, level = Counter(
            (e["department_id"], e["level_id"]) for e in data.employees
        ).most_common(1)[0][0]
        expected = {
            e["id"] for e in data.employees if e["department_id"] == dept and e["level_id"] == level
        }

        body = client.get(URL, params={"department_id": dept, "level_id": level}).json()

        assert body["total"] == len(expected)
        assert {i["id"] for i in body["items"]} == expected

    def test_salary_range_filters_on_current_usd_base(
        self, client: TestClient, data: SeedData
    ) -> None:
        low, high = Decimal("30000"), Decimal("90000")
        expected = {
            emp_id for emp_id, r in _current(data).items() if low <= r["base_amount_usd"] <= high
        }

        body = client.get(
            URL, params={"min_salary_usd": low, "max_salary_usd": high, "page_size": 200}
        ).json()

        assert {i["id"] for i in body["items"]} == expected

    def test_search_matches_full_name_case_insensitively(
        self, client: TestClient, data: SeedData
    ) -> None:
        emp = data.employees[0]
        term = f"{emp['first_name']} {emp['last_name']}".upper()

        items = client.get(URL, params={"q": term}).json()["items"]

        assert emp["id"] in {i["id"] for i in items}
        assert all(f"{i['first_name']} {i['last_name']}".upper() == term for i in items)

    def test_search_treats_like_wildcards_literally(
        self, client: TestClient, data: SeedData
    ) -> None:
        assert client.get(URL, params={"q": "%"}).json()["total"] == 0

    def test_sort_by_salary_descending(self, client: TestClient, data: SeedData) -> None:
        items = client.get(
            URL, params={"sort": "base_salary_usd", "order": "desc", "page_size": 60}
        ).json()["items"]

        salaries = [Decimal(i["base_amount_usd"]) for i in items]
        assert salaries == sorted(salaries, reverse=True)

    @pytest.mark.parametrize(
        "params",
        [
            {"page": 0},
            {"page_size": 500},
            {"sort": "salary"},
            {"min_salary_usd": 10, "max_salary_usd": 5},
            {"unknown": 1},
        ],
    )
    def test_rejects_invalid_query(self, client: TestClient, data: SeedData, params: dict) -> None:
        assert client.get(URL, params=params).status_code == 422


def test_filter_options(client: TestClient, data: SeedData) -> None:
    body = client.get(f"{URL}/filters").json()

    assert len(body["departments"]) == 8
    assert len(body["roles"]) == 30
    assert [lvl["code"] for lvl in body["levels"]] == ["L1", "L2", "L3", "L4", "L5"]
    assert len(body["countries"]) == 6
    assert body["statuses"] == ["active", "on_leave", "terminated"]
    current_usd = [r["base_amount_usd"] for r in _current(data).values()]
    assert Decimal(body["salary_usd_min"]) == min(current_usd)
    assert Decimal(body["salary_usd_max"]) == max(current_usd)


class TestDetail:
    def test_profile_and_history_newest_first(self, client: TestClient, data: SeedData) -> None:
        emp = next(e for e in data.employees if e["manager_id"])

        body = client.get(f"{URL}/{emp['id']}").json()

        assert body["employee_code"] == emp["employee_code"]
        assert body["manager"]["id"] == emp["manager_id"]
        history = body["salary_history"]
        assert [h["effective_from"] for h in history] == sorted(
            (h["effective_from"] for h in history), reverse=True
        )
        assert [h["is_current"] for h in history].count(True) == 1
        assert body["current_salary"] == history[0]
        assert history[-1]["reason"] == "hire"

    def test_unknown_employee_is_404(self, client: TestClient, data: SeedData) -> None:
        response = client.get(f"{URL}/999999")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "employee_not_found"


class TestWrites:
    def _payload(self, data: SeedData, **overrides: object) -> dict:
        role = data.job_roles[0]
        payload = {
            "employee_code": "N00001",
            "first_name": "New",
            "last_name": "Hire",
            "email": "new.hire@acme.example",
            "department_id": role["department_id"],
            "role_id": role["id"],
            "level_id": 2,
            "country_id": 1,  # US, USD
            "hire_date": "2026-08-01",
            "base_amount": "120000.00",
            "bonus_amount": "10000.00",
        }
        payload.update(overrides)
        return payload

    def test_create_then_read_back(self, client: TestClient, data: SeedData) -> None:
        response = client.post(URL, json=self._payload(data))

        assert response.status_code == 201
        body = response.json()
        assert body["current_salary"]["reason"] == "hire"
        assert body["current_salary"]["base_amount_usd"] == "120000.00"
        assert body["current_salary"]["band_id"] is not None  # exact seeded band
        assert body["net_pay"]["tax_amount"] == "12000.00"
        assert body["net_pay"]["net_amount"] == "108000.00"
        assert client.get(f"{URL}/{body['id']}").json() == body
        assert client.get(URL, params={"q": "N00001"}).json()["total"] == 1

    def test_duplicate_code_is_409(self, client: TestClient, data: SeedData) -> None:
        response = client.post(URL, json=self._payload(data, employee_code="E00001"))

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "duplicate_employee"

    def test_role_outside_department_is_422(self, client: TestClient, data: SeedData) -> None:
        other = next(
            r for r in data.job_roles if r["department_id"] != data.job_roles[0]["department_id"]
        )
        response = client.post(URL, json=self._payload(data, role_id=other["id"]))

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_reference"

    def test_patch_level_then_country_change_is_refused(
        self, client: TestClient, data: SeedData
    ) -> None:
        emp = next(e for e in data.employees if e["level_id"] < 5)

        promoted = client.patch(f"{URL}/{emp['id']}", json={"level_id": emp["level_id"] + 1})
        assert promoted.status_code == 200
        assert promoted.json()["level"]["id"] == emp["level_id"] + 1

        other_country = 2 if emp["country_id"] != 2 else 3
        moved = client.patch(f"{URL}/{emp['id']}", json={"country_id": other_country})
        assert moved.status_code == 422
        assert moved.json()["error"]["code"] == "invalid_employee_change"
