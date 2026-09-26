import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_error_handlers
from app.core.exceptions import (
    BandNotFound,
    CurrencyMismatch,
    DomainError,
    DuplicateEmployee,
    EmployeeNotFound,
    InvalidEffectiveDate,
)


def _client_raising(error: DomainError) -> TestClient:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise error

    return TestClient(app)


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (EmployeeNotFound("no such employee"), 404, "employee_not_found"),
        (BandNotFound("no band"), 404, "band_not_found"),
        (DuplicateEmployee("code taken"), 409, "duplicate_employee"),
        (InvalidEffectiveDate("overlaps"), 422, "invalid_effective_date"),
        (CurrencyMismatch("INR vs USD"), 422, "currency_mismatch"),
        (DomainError("unclassified"), 400, "domain_error"),
    ],
)
def test_domain_errors_map_to_http_status_and_stable_code(
    error: DomainError, status: int, code: str
) -> None:
    response = _client_raising(error).get("/boom")

    assert response.status_code == status
    assert response.json() == {"error": {"code": code, "message": error.message}}
