from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Input money: fits DECIMAL(14,2) exactly, so nothing is rounded on the way in.
Money = Annotated[Decimal, Field(max_digits=14, decimal_places=2)]


class Schema(BaseModel):
    """Base for response DTOs. Built from ORM rows, never returned as ORM rows.

    Decimal money is serialised as a JSON string, so no amount goes through a float.
    """

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class DepartmentOut(Schema):
    id: int
    name: str


class RoleOut(Schema):
    id: int
    name: str
    department_id: int


class LevelOut(Schema):
    id: int
    code: str
    name: str
    rank: int
    min_years: int
    max_years: int | None


class CountryOut(Schema):
    id: int
    code: str
    name: str
    currency_code: str


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
