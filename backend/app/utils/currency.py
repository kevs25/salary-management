from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def to_money(amount: Decimal) -> Decimal:
    """Round to the 2 decimal places that DECIMAL(14,2) stores, half-up like finance does.

    Rounding here, rather than letting MySQL truncate on insert, keeps the value the
    service computed identical to the value that gets stored.
    """
    if not isinstance(amount, Decimal):
        raise TypeError(f"money must be Decimal, got {type(amount).__name__}")
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def to_usd(amount: Decimal, rate_to_usd: Decimal) -> Decimal:
    """Convert a local-currency amount with a snapshot rate (1 unit local = rate USD)."""
    if not isinstance(rate_to_usd, Decimal):
        raise TypeError(f"rate must be Decimal, got {type(rate_to_usd).__name__}")
    if rate_to_usd <= 0:
        raise ValueError("rate_to_usd must be positive")
    return to_money(amount * rate_to_usd)
