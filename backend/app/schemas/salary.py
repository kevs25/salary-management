from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import ChangeReason
from app.schemas.common import Money, Schema


class SalaryRecordOut(Schema):
    id: int
    currency_code: str
    base_amount: Decimal
    bonus_amount: Decimal
    fx_rate_to_usd: Decimal
    base_amount_usd: Decimal
    bonus_amount_usd: Decimal
    effective_from: date
    effective_to: date | None
    is_current: bool
    reason: ChangeReason
    note: str | None
    band_id: int | None


# A revision can't be a hire; hires are created with the employee.
RevisionReason = Literal[
    ChangeReason.PROMOTION,
    ChangeReason.MERIT,
    ChangeReason.MARKET_ADJUSTMENT,
    ChangeReason.CORRECTION,
]


class SalaryRevisionCreate(BaseModel):
    """New pay from effective_from onwards. The current record is closed, not edited."""

    model_config = ConfigDict(extra="forbid")

    base_amount: Annotated[Money, Field(gt=0, description="annual, local currency")]
    bonus_amount: Annotated[Money, Field(ge=0, description="annual, local currency")] = Decimal("0")
    currency_code: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{3}$"),
        Field(description="optional check: must be the employee's country currency"),
    ] = None
    effective_from: date
    reason: RevisionReason
    note: Annotated[str | None, StringConstraints(strip_whitespace=True, max_length=255)] = None


class SalaryRevisionOut(Schema):
    previous: SalaryRecordOut
    current: SalaryRecordOut
    base_change_pct: Decimal = Field(description="change in base pay, percent, 2 dp")
