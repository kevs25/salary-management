"""Domain errors raised by services.

These must not import FastAPI. The mapping to HTTP status codes lives in
app/api/errors.py, so services stay framework-agnostic.
"""


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
