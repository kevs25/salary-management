import pytest

from app.services.band import (
    DEPARTMENT_LEVEL,
    DEPARTMENT_LEVEL_COUNTRY,
    EXACT,
    BandCell,
    BandResolver,
)
from tests.unit.fakes import FakeBandLookup

CELL = BandCell(department_id=1, role_id=10, level_id=3, country_id=5)


@pytest.fixture
def lookup() -> FakeBandLookup:
    return FakeBandLookup()


def test_exact_band_wins_over_every_fallback(lookup: FakeBandLookup) -> None:
    exact = lookup.add(department_id=1, level_id=3, role_id=10, country_id=5)
    lookup.add(department_id=1, level_id=3, role_id=None, country_id=5)
    lookup.add(department_id=1, level_id=3, role_id=None, country_id=None)

    resolved = BandResolver(lookup).resolve(CELL)

    assert resolved is not None
    assert resolved.band is exact
    assert resolved.strategy is EXACT
    assert lookup.calls == [(1, 3, 10, 5)]  # stops at the first hit


def test_falls_back_to_department_level_country_when_role_has_no_band(
    lookup: FakeBandLookup,
) -> None:
    fallback = lookup.add(department_id=1, level_id=3, role_id=None, country_id=5)
    lookup.add(department_id=1, level_id=3, role_id=None, country_id=None)

    resolved = BandResolver(lookup).resolve(CELL)

    assert resolved is not None
    assert resolved.band is fallback
    assert resolved.strategy is DEPARTMENT_LEVEL_COUNTRY


def test_falls_back_to_department_level_when_country_has_no_band(
    lookup: FakeBandLookup,
) -> None:
    fallback = lookup.add(department_id=1, level_id=3, role_id=None, country_id=None)

    resolved = BandResolver(lookup).resolve(CELL)

    assert resolved is not None
    assert resolved.band is fallback
    assert resolved.strategy is DEPARTMENT_LEVEL
    assert lookup.calls == [(1, 3, 10, 5), (1, 3, None, 5), (1, 3, None, None)]


def test_bands_for_other_roles_countries_or_levels_do_not_match(
    lookup: FakeBandLookup,
) -> None:
    lookup.add(department_id=1, level_id=3, role_id=11, country_id=5)  # other role
    lookup.add(department_id=1, level_id=3, role_id=None, country_id=6)  # other country
    lookup.add(department_id=1, level_id=4, role_id=None, country_id=None)  # other level
    lookup.add(department_id=2, level_id=3, role_id=None, country_id=None)  # other dept

    assert BandResolver(lookup).resolve(CELL) is None


def test_role_band_without_country_is_not_part_of_the_chain(lookup: FakeBandLookup) -> None:
    # dept+role+level (no country) is not a policy level we resolve to.
    lookup.add(department_id=1, level_id=3, role_id=10, country_id=None)

    assert BandResolver(lookup).resolve(CELL) is None


def test_strategy_order_is_configurable(lookup: FakeBandLookup) -> None:
    lookup.add(department_id=1, level_id=3, role_id=10, country_id=5)
    broad = lookup.add(department_id=1, level_id=3, role_id=None, country_id=None)

    resolved = BandResolver(lookup, strategies=(DEPARTMENT_LEVEL, EXACT)).resolve(CELL)

    assert resolved is not None
    assert resolved.band is broad
