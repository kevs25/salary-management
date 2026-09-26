"""Band resolution: which pay band applies to a (department, role, level, country) cell.

The policy is an ordered list of strategies, most specific first. The first one
with a band defined wins. Adding or reordering a fallback means editing
BAND_RESOLUTION_ORDER, not a nested if.
"""

from dataclasses import dataclass
from typing import Protocol

from app.models import SalaryBand


@dataclass(frozen=True)
class BandCell:
    department_id: int
    role_id: int
    level_id: int
    country_id: int


class BandLookup(Protocol):
    def find_band(
        self,
        *,
        department_id: int,
        level_id: int,
        role_id: int | None,
        country_id: int | None,
    ) -> SalaryBand | None: ...


@dataclass(frozen=True)
class BandStrategy:
    """One step in the fallback chain: which parts of the cell it matches on."""

    name: str
    match_role: bool
    match_country: bool

    def find(self, cell: BandCell, lookup: BandLookup) -> SalaryBand | None:
        return lookup.find_band(
            department_id=cell.department_id,
            level_id=cell.level_id,
            role_id=cell.role_id if self.match_role else None,
            country_id=cell.country_id if self.match_country else None,
        )


EXACT = BandStrategy("department+role+level+country", match_role=True, match_country=True)
DEPARTMENT_LEVEL_COUNTRY = BandStrategy(
    "department+level+country", match_role=False, match_country=True
)
DEPARTMENT_LEVEL = BandStrategy("department+level", match_role=False, match_country=False)

BAND_RESOLUTION_ORDER: tuple[BandStrategy, ...] = (
    EXACT,
    DEPARTMENT_LEVEL_COUNTRY,
    DEPARTMENT_LEVEL,
)


@dataclass(frozen=True)
class ResolvedBand:
    band: SalaryBand
    strategy: BandStrategy


class BandResolver:
    def __init__(
        self, lookup: BandLookup, strategies: tuple[BandStrategy, ...] = BAND_RESOLUTION_ORDER
    ) -> None:
        self._lookup = lookup
        self._strategies = strategies

    def resolve(self, cell: BandCell) -> ResolvedBand | None:
        """The most specific band defined for the cell, or None if no policy covers it."""
        for strategy in self._strategies:
            band = strategy.find(cell, self._lookup)
            if band is not None:
                return ResolvedBand(band=band, strategy=strategy)
        return None
