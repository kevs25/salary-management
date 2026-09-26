"""Band management endpoints against real MySQL, on the generated band set (900 bands)."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert
from sqlalchemy.orm import Session

from app.seed.generator import SeedData, generate
from app.seed.seed import LOAD_ORDER

URL = "/api/v1/bands"


@pytest.fixture
def data(db_session: Session) -> SeedData:
    data = generate(seed=11, employee_count=20)
    for model, attr in LOAD_ORDER:
        db_session.execute(insert(model.__table__), getattr(data, attr))
    db_session.flush()
    return data


def _unused_band(data: SeedData) -> dict:
    used = {r["band_id"] for r in data.salary_records}
    return next(b for b in data.salary_bands if b["id"] not in used)


class TestList:
    def test_all_seeded_bands_are_exact_and_paginated(
        self, client: TestClient, data: SeedData
    ) -> None:
        body = client.get(URL, params={"page_size": 200}).json()

        assert body["total"] == len(data.salary_bands) == 900
        assert len(body["items"]) == 200
        assert {b["scope"] for b in body["items"]} == {"department+role+level+country"}

    def test_filters_narrow_to_one_cell(self, client: TestClient, data: SeedData) -> None:
        band = data.salary_bands[0]

        body = client.get(
            URL,
            params={
                "department_id": band["department_id"],
                "role_id": band["role_id"],
                "level_id": band["level_id"],
                "country_id": band["country_id"],
            },
        ).json()

        assert body["total"] == 1
        item = body["items"][0]
        assert item["id"] == band["id"]
        assert item["department"]["id"] == band["department_id"]
        assert item["role"]["id"] == band["role_id"]
        assert item["country"]["currency_code"] == band["currency_code"]
        assert Decimal(item["mid_amount"]) == band["mid_amount"]

    def test_fallback_bands_sort_first_and_filter_by_scope(
        self, client: TestClient, data: SeedData
    ) -> None:
        band = data.salary_bands[0]
        cell = {"department_id": band["department_id"], "level_id": band["level_id"]}
        client.post(URL, json=cell | {"min_amount": "1", "mid_amount": "2", "max_amount": "3"})

        in_cell = client.get(URL, params=cell | {"page_size": 200}).json()["items"]
        assert in_cell[0]["scope"] == "department+level"
        assert in_cell[0]["currency_code"] == "USD"

        fallback = client.get(URL, params={"scope": "department+level"}).json()
        assert fallback["total"] == 1


class TestWrites:
    def test_create_read_update(self, client: TestClient, data: SeedData) -> None:
        band = data.salary_bands[0]
        created = client.post(
            URL,
            json={
                "department_id": band["department_id"],
                "level_id": band["level_id"],
                "country_id": band["country_id"],
                "min_amount": "1000.00",
                "mid_amount": "1200.00",
                "max_amount": "1400.00",
            },
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["scope"] == "department+level+country"
        assert body["role"] is None
        assert body["currency_code"] == band["currency_code"]
        assert client.get(f"{URL}/{body['id']}").json() == body

        updated = client.patch(f"{URL}/{body['id']}", json={"max_amount": "1500.00"})
        assert updated.status_code == 200
        assert updated.json()["max_amount"] == "1500.00"
        assert updated.json()["min_amount"] == "1000.00"

    def test_duplicate_scope_is_409(self, client: TestClient, data: SeedData) -> None:
        band = data.salary_bands[0]
        response = client.post(
            URL,
            json={
                "department_id": band["department_id"],
                "role_id": band["role_id"],
                "level_id": band["level_id"],
                "country_id": band["country_id"],
                "min_amount": "1",
                "mid_amount": "2",
                "max_amount": "3",
            },
        )

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "duplicate_band"

    def test_unordered_amounts_on_update_are_422(self, client: TestClient, data: SeedData) -> None:
        band = data.salary_bands[0]

        response = client.patch(
            f"{URL}/{band['id']}", json={"min_amount": f"{band['max_amount'] + 1}"}
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_band"
        assert client.get(f"{URL}/{band['id']}").json()["min_amount"] == str(band["min_amount"])

    def test_role_without_country_is_422(self, client: TestClient, data: SeedData) -> None:
        band = data.salary_bands[0]
        response = client.post(
            URL,
            json={
                "department_id": band["department_id"],
                "role_id": band["role_id"],
                "level_id": band["level_id"],
                "min_amount": "1",
                "mid_amount": "2",
                "max_amount": "3",
            },
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "invalid_band"


class TestDelete:
    def test_unused_band_is_deleted(self, client: TestClient, data: SeedData) -> None:
        band = _unused_band(data)

        assert client.delete(f"{URL}/{band['id']}").status_code == 204
        assert client.get(f"{URL}/{band['id']}").status_code == 404

    def test_band_in_salary_history_is_409(self, client: TestClient, data: SeedData) -> None:
        band_id = data.salary_records[0]["band_id"]

        response = client.delete(f"{URL}/{band_id}")

        assert response.status_code == 409
        assert response.json()["error"]["code"] == "band_in_use"
        assert client.get(f"{URL}/{band_id}").status_code == 200


def test_new_fallback_band_is_picked_up_by_the_resolver(
    client: TestClient, db_session: Session, data: SeedData
) -> None:
    """A dept+level band created through the API is what a new hire links to
    when their exact cell has no band."""
    band = _unused_band(data)
    assert client.delete(f"{URL}/{band['id']}").status_code == 204
    fallback = client.post(
        URL,
        json={
            "department_id": band["department_id"],
            "level_id": band["level_id"],
            "min_amount": "50000.00",
            "mid_amount": "60000.00",
            "max_amount": "70000.00",
        },
    ).json()

    hire = client.post(
        "/api/v1/employees",
        json={
            "employee_code": "N00001",
            "first_name": "New",
            "last_name": "Hire",
            "email": "new.hire@acme.example",
            "department_id": band["department_id"],
            "role_id": band["role_id"],
            "level_id": band["level_id"],
            "country_id": band["country_id"],
            "hire_date": "2026-08-01",
            "base_amount": "100000.00",
        },
    )

    assert hire.status_code == 201, hire.text
    assert hire.json()["current_salary"]["band_id"] == fallback["id"]
