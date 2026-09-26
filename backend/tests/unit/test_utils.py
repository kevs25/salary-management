from decimal import Decimal

import pytest

from app.utils.currency import to_money, to_usd
from app.utils.pagination import MAX_PAGE_SIZE, PageParams


class TestToUsd:
    def test_converts_with_snapshot_rate(self) -> None:
        assert to_usd(Decimal("1200000.00"), Decimal("0.01200000")) == Decimal("14400.00")

    def test_rounds_half_up_to_cents(self) -> None:
        # 1000.00 * 0.01234567 = 12.34567 -> 12.35
        assert to_usd(Decimal("1000.00"), Decimal("0.01234567")) == Decimal("12.35")
        # exactly half a cent rounds up, not to even
        assert to_usd(Decimal("0.25"), Decimal("0.1")) == Decimal("0.03")

    def test_rejects_float(self) -> None:
        with pytest.raises(TypeError):
            to_usd(1000.0, Decimal("1"))  # type: ignore[arg-type]
        with pytest.raises(TypeError):
            to_usd(Decimal("1000"), 1.0)  # type: ignore[arg-type]

    def test_rejects_non_positive_rate(self) -> None:
        with pytest.raises(ValueError):
            to_usd(Decimal("1000"), Decimal("0"))


def test_to_money_quantizes_to_two_places() -> None:
    assert to_money(Decimal("10")) == Decimal("10.00")
    assert str(to_money(Decimal("10"))) == "10.00"


class TestPageParams:
    def test_offset_is_zero_based_from_one_based_page(self) -> None:
        assert PageParams(page=1, page_size=50).offset == 0
        assert PageParams(page=3, page_size=50).offset == 100
        assert PageParams(page=3, page_size=50).limit == 50

    @pytest.mark.parametrize(("page", "page_size"), [(0, 50), (1, 0), (1, MAX_PAGE_SIZE + 1)])
    def test_rejects_out_of_range(self, page: int, page_size: int) -> None:
        with pytest.raises(ValueError):
            PageParams(page=page, page_size=page_size)

    def test_accepts_max_page_size(self) -> None:
        assert PageParams(page_size=MAX_PAGE_SIZE).limit == MAX_PAGE_SIZE
