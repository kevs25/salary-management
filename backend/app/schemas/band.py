from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import BandScope
from app.schemas.common import CountryOut, DepartmentOut, LevelOut, Money, RoleOut, Schema
from app.utils.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageParams

BandAmount = Annotated[Money, Field(gt=0, description="annual base, band currency")]


class BandQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department_id: int | None = None
    role_id: int | None = None
    level_id: int | None = None
    country_id: int | None = None
    scope: BandScope | None = None
    page: Annotated[int, Field(ge=1)] = 1
    page_size: Annotated[int, Field(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE

    @property
    def page_params(self) -> PageParams:
        return PageParams(page=self.page, page_size=self.page_size)


class BandOut(Schema):
    id: int
    scope: BandScope
    department: DepartmentOut
    role: RoleOut | None = Field(description="null: applies to every role in the department")
    level: LevelOut
    country: CountryOut | None = Field(description="null: applies in every country, in USD")
    currency_code: str
    min_amount: Decimal
    mid_amount: Decimal
    max_amount: Decimal
    updated_at: datetime


class BandCreate(BaseModel):
    """A band for one scope. Leave role_id and/or country_id out for a fallback band.

    The currency is not sent: it is the country's currency, or USD for a band that
    applies in every country.
    """

    model_config = ConfigDict(extra="forbid")

    department_id: int
    role_id: int | None = None
    level_id: int
    country_id: int | None = None
    min_amount: BandAmount
    mid_amount: BandAmount
    max_amount: BandAmount


class BandUpdate(BaseModel):
    """New amounts for an existing band. Its scope is fixed; create a new band instead."""

    model_config = ConfigDict(extra="forbid")

    min_amount: BandAmount | None = None
    mid_amount: BandAmount | None = None
    max_amount: BandAmount | None = None

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if self.min_amount is None and self.mid_amount is None and self.max_amount is None:
            raise ValueError("send at least one of min_amount, mid_amount, max_amount")
        return self
