from fastapi import APIRouter, status

from app.core.dependencies import SalaryServiceDep
from app.schemas.common import ErrorResponse
from app.schemas.salary import SalaryRevisionCreate, SalaryRevisionOut

router = APIRouter(prefix="/employees/{employee_id}/salary-revisions", tags=["salaries"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def revise_salary(
    employee_id: int, payload: SalaryRevisionCreate, service: SalaryServiceDep
) -> SalaryRevisionOut:
    """Close the current pay record and open a new one from effective_from."""
    return service.revise_salary(employee_id, payload)
