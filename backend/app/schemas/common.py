from pydantic import BaseModel, ConfigDict


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
