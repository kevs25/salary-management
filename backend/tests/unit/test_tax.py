from decimal import Decimal

from app.services.tax import net_pay


def test_deducts_ten_percent_in_local_currency() -> None:
    pay = net_pay(Decimal("1500000.00"), "INR")

    assert pay.currency_code == "INR"
    assert pay.tax_amount == Decimal("150000.00")
    assert pay.net_amount == Decimal("1350000.00")


def test_tax_rounds_half_up_and_net_absorbs_the_cent() -> None:
    # 10% of 0.05 is 0.005 -> 0.01; tax + net always adds back to base
    pay = net_pay(Decimal("1000.05"), "USD")

    assert pay.tax_amount == Decimal("100.01")
    assert pay.net_amount == Decimal("900.04")
    assert pay.tax_amount + pay.net_amount == pay.base_amount
