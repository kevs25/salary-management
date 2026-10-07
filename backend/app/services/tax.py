from decimal import Decimal

from app.schemas.employee import NetPay
from app.utils.currency import to_money

# One flat, indicative rate for every country. Not a statutory calculation:
# real per-country tax is out of scope (REQUIREMENTS.md section 5).
TAX_RATE = Decimal("0.10")


def net_pay(base_amount: Decimal, currency_code: str) -> NetPay:
    """Base pay less the flat tax deduction, in the salary's own currency.

    Derived on read from the current salary record, never stored, so it cannot
    drift from the salary after a revision.
    """
    tax = to_money(base_amount * TAX_RATE)
    return NetPay(
        currency_code=currency_code,
        base_amount=base_amount,
        tax_rate=TAX_RATE,
        tax_amount=tax,
        net_amount=base_amount - tax,
    )
