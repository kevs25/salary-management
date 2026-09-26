from typing import Annotated

from fastapi import APIRouter, Query, status

from app.core.dependencies import EmployeeServiceDep
from app.schemas.common import ErrorResponse, Page
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeDetail,
    EmployeeFilterOptions,
    EmployeeListItem,
    EmployeeQuery,
    EmployeeUpdate,
)

router = APIRouter(prefix="/employees", tags=["employees"])

_NOT_FOUND = {404: {"model": ErrorResponse}}
_WRITE_ERRORS = {409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}}


@router.get("")
def list_employees(
    query: Annotated[EmployeeQuery, Query()], service: EmployeeServiceDep
) -> Page[EmployeeListItem]:
    return service.list_employees(query)


@router.get("/filters")
def employee_filter_options(service: EmployeeServiceDep) -> EmployeeFilterOptions:
    return service.filter_options()


@router.get("/{employee_id}", responses=_NOT_FOUND)
def get_employee(employee_id: int, service: EmployeeServiceDep) -> EmployeeDetail:
    return service.get_employee(employee_id)


@router.post("", status_code=status.HTTP_201_CREATED, responses=_WRITE_ERRORS)
def create_employee(payload: EmployeeCreate, service: EmployeeServiceDep) -> EmployeeDetail:
    return service.create_employee(payload)


@router.patch("/{employee_id}", responses=_NOT_FOUND | _WRITE_ERRORS)
def update_employee(
    employee_id: int, payload: EmployeeUpdate, service: EmployeeServiceDep
) -> EmployeeDetail:
    return service.update_employee(employee_id, payload)
