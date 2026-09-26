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


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
