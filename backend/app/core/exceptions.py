"""Domain exceptions, and the one handler that maps them to HTTP responses.

Services raise these and never build HTTP responses themselves; the status code
for each error family is decided only in _STATUS_BY_ERROR below.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    code = "not_found"


class ConflictError(DomainError):
    code = "conflict"


class BusinessRuleViolation(DomainError):
    code = "business_rule_violation"


class EmployeeNotFound(NotFoundError):
    code = "employee_not_found"


class BandNotFound(NotFoundError):
    code = "band_not_found"


class DuplicateEmployee(ConflictError):
    code = "duplicate_employee"


class InvalidEffectiveDate(BusinessRuleViolation):
    code = "invalid_effective_date"


class CurrencyMismatch(BusinessRuleViolation):
    code = "currency_mismatch"


class InvalidReference(BusinessRuleViolation):
    """A payload points at a department/role/level/country/manager that doesn't fit."""

    code = "invalid_reference"


class InvalidEmployeeChange(BusinessRuleViolation):
    code = "invalid_employee_change"


class MissingFxRate(BusinessRuleViolation):
    code = "missing_fx_rate"


class InvalidSalaryRevision(BusinessRuleViolation):
    code = "invalid_salary_revision"


# Most specific first; the first isinstance match wins.
_STATUS_BY_ERROR: list[tuple[type[DomainError], int]] = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (BusinessRuleViolation, status.HTTP_422_UNPROCESSABLE_CONTENT),
]


def status_for(exc: DomainError) -> int:
    for error_type, code in _STATUS_BY_ERROR:
        if isinstance(exc, error_type):
            return code
    return status.HTTP_400_BAD_REQUEST


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=status_for(exc),
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
