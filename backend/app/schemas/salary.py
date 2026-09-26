from datetime import date
from decimal import Decimal

from app.models import ChangeReason
from app.schemas.common import Schema


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
