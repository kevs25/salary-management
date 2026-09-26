"""Salary revision endpoint against real MySQL, on a small generated dataset."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_today
from app.models import SalaryRecord
from app.seed import reference_data as ref
from app.seed.generator import SeedData, generate
from app.seed.seed import LOAD_ORDER

TODAY = ref.AS_OF  # the dataset's "today"; keeps the tests independent of the wall clock


@pytest.fixture
def data(db_session: Session, client: TestClient) -> SeedData:
    data = generate(seed=11, employee_count=30)
    for model, attr in LOAD_ORDER:
        db_session.execute(insert(model.__table__), getattr(data, attr))
    db_session.flush()
    client.app.dependency_overrides[get_today] = lambda: lambda: TODAY
    return data


def _employee(data: SeedData, **match: object) -> dict:
    return next(e for e in data.employees if all(e[k] == v for k, v in match.items()))


def _current(data: SeedData, employee_id: int) -> dict:
    return next(
        r for r in data.salary_records if r["employee_id"] == employee_id and r["is_current"]
    )


def _url(employee_id: int) -> str:
    return f"/api/v1/employees/{employee_id}/salary-revisions"


def _current_count(db_session: Session, employee_id: int) -> int:
    return db_session.scalar(
        select(func.count())
        .select_from(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id, SalaryRecord.is_current.is_(True))
    )


def test_revision_closes_current_and_opens_new(
    client: TestClient, db_session: Session, data: SeedData
) -> None:
    emp = _employee(data, status="active")
    before = _current(data, emp["id"])
    new_base = before["base_amount"] * Decimal("1.10")

    response = client.post(
        _url(emp["id"]),
        json={
            "base_amount": f"{new_base:.2f}",
            "bonus_amount": "0",
            "effective_from": TODAY.isoformat(),
            "reason": "merit",
            "note": "annual review",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["previous"]["id"] == before["id"]
    assert body["previous"]["effective_to"] == TODAY.isoformat()
    assert body["previous"]["is_current"] is False
    assert body["current"]["is_current"] is True
    assert body["current"]["band_id"] is not None
    assert Decimal(body["base_change_pct"]) == Decimal("10.00")

    detail = client.get(f"/api/v1/employees/{emp['id']}").json()
    assert detail["current_salary"]["id"] == body["current"]["id"]
    assert detail["salary_history"][1]["id"] == before["id"]
    listed = client.get("/api/v1/employees", params={"q": emp["employee_code"]}).json()
    assert Decimal(listed["items"][0]["base_amount"]) == Decimal(f"{new_base:.2f}")
    assert _current_count(db_session, emp["id"]) == 1


def test_consecutive_revisions_keep_one_current_record(
    client: TestClient, db_session: Session, data: SeedData
) -> None:
    emp = next(
        e
        for e in data.employees
        if e["status"] == "active" and _current(data, e["id"])["effective_from"] < date(2026, 8, 1)
    )

    for base, day in (("100000.00", "2026-08-01"), ("110000.00", "2026-09-01")):
        # Local-currency amounts; the values only need to differ from the current pay.
        response = client.post(
            _url(emp["id"]),
            json={"base_amount": base, "effective_from": day, "reason": "market_adjustment"},
        )
        assert response.status_code == 201, response.text

    assert _current_count(db_session, emp["id"]) == 1
    history = client.get(f"/api/v1/employees/{emp['id']}").json()["salary_history"]
    assert history[0]["effective_from"] == "2026-09-01"
    assert history[1]["effective_to"] == "2026-09-01"
    assert history[1]["effective_from"] == "2026-08-01"
    assert history[2]["effective_to"] == "2026-08-01"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"effective_from": "current_start"}, "invalid_effective_date"),
        ({"effective_from": "2026-09-02"}, "invalid_effective_date"),
        ({"currency_code": "XXX"}, "currency_mismatch"),
    ],
)
def test_rule_violations_are_422_and_change_nothing(
    client: TestClient, db_session: Session, data: SeedData, payload: dict, code: str
) -> None:
    emp = _employee(data, status="active")
    current = _current(data, emp["id"])
    body = {"base_amount": "1.00", "effective_from": TODAY.isoformat(), "reason": "merit"}
    body.update(payload)
    if body["effective_from"] == "current_start":
        body["effective_from"] = current["effective_from"].isoformat()

    response = client.post(_url(emp["id"]), json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    detail = client.get(f"/api/v1/employees/{emp['id']}").json()
    assert detail["current_salary"]["id"] == current["id"]


def test_terminated_employee_is_422(client: TestClient, data: SeedData) -> None:
    emp = data.employees[0]
    assert client.patch(f"/api/v1/employees/{emp['id']}", json={"status": "terminated"}).is_success

    response = client.post(
        _url(emp["id"]),
        json={"base_amount": "1.00", "effective_from": TODAY.isoformat(), "reason": "merit"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_salary_revision"


def test_unknown_employee_is_404(client: TestClient, data: SeedData) -> None:
    response = client.post(
        _url(999999),
        json={"base_amount": "1.00", "effective_from": TODAY.isoformat(), "reason": "merit"},
    )

    assert response.status_code == 404


def test_hire_is_not_a_revision_reason(client: TestClient, data: SeedData) -> None:
    response = client.post(
        _url(data.employees[0]["id"]),
        json={"base_amount": "1.00", "effective_from": TODAY.isoformat(), "reason": "hire"},
    )

    assert response.status_code == 422
