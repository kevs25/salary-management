"""Salary bands: the org's pay policy, and which band applies to a given cell.

Resolution is an ordered list of strategies, most specific first. The first one
with a band defined wins. Adding or reordering a fallback means editing
BAND_RESOLUTION_ORDER, not a nested if.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.database import UnitOfWork
from app.core.exceptions import (
    BandInUse,
    BandNotFound,
    DuplicateBand,
    InvalidBand,
    InvalidReference,
)
from app.models import BandScope, SalaryBand
from app.schemas.band import BandCreate, BandOut, BandQuery, BandUpdate
from app.schemas.common import Page

# A band that applies in every country has no local currency; it is priced in USD.
FALLBACK_BAND_CURRENCY = "USD"

# Resolution


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

    scope: BandScope
    match_role: bool
    match_country: bool

    def find(self, cell: BandCell, lookup: BandLookup) -> SalaryBand | None:
        return lookup.find_band(
            department_id=cell.department_id,
            level_id=cell.level_id,
            role_id=cell.role_id if self.match_role else None,
            country_id=cell.country_id if self.match_country else None,
        )


EXACT = BandStrategy(BandScope.EXACT, match_role=True, match_country=True)
DEPARTMENT_LEVEL_COUNTRY = BandStrategy(
    BandScope.DEPARTMENT_LEVEL_COUNTRY, match_role=False, match_country=True
)
DEPARTMENT_LEVEL = BandStrategy(BandScope.DEPARTMENT_LEVEL, match_role=False, match_country=False)

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


# Management


class BandRepositoryPort(BandLookup, Protocol):
    def list(self, query: BandQuery) -> tuple[list[SalaryBand], int]: ...
    def get(self, entity_id: int) -> SalaryBand | None: ...
    def get_detail(self, band_id: int) -> SalaryBand | None: ...
    def add(self, entity: SalaryBand) -> SalaryBand: ...
    def is_referenced(self, band_id: int) -> bool: ...
    def delete(self, band: SalaryBand) -> None: ...


class ReferenceLookup(Protocol):
    def department_exists(self, department_id: int) -> bool: ...
    def level_exists(self, level_id: int) -> bool: ...
    def role_department_id(self, role_id: int) -> int | None: ...
    def country_currency(self, country_id: int) -> str | None: ...


class BandService:
    """Viewing and editing the pay policy.

    Editing a band changes policy from now on; salary records are not touched.
    Compliance and compa-ratio read the band as it is today.
    """

    def __init__(
        self, bands: BandRepositoryPort, references: ReferenceLookup, uow: UnitOfWork
    ) -> None:
        self._bands = bands
        self._references = references
        self._uow = uow

    def list_bands(self, query: BandQuery) -> Page[BandOut]:
        bands, total = self._bands.list(query)
        return Page(
            items=[BandOut.model_validate(b) for b in bands],
            total=total,
            page=query.page,
            page_size=query.page_size,
        )

    def get_band(self, band_id: int) -> BandOut:
        band = self._bands.get_detail(band_id)
        if band is None:
            raise BandNotFound(f"Band {band_id} not found")
        return BandOut.model_validate(band)

    def create_band(self, payload: BandCreate) -> BandOut:
        scope = BandScope.of(
            has_role=payload.role_id is not None, has_country=payload.country_id is not None
        )
        if scope is None:
            raise InvalidBand(
                "A role-specific band must also name a country; "
                "use a department-wide band to cover every country"
            )
        currency = self._check_scope(payload)
        _check_amounts(payload.min_amount, payload.mid_amount, payload.max_amount)
        existing = self._bands.find_band(
            department_id=payload.department_id,
            level_id=payload.level_id,
            role_id=payload.role_id,
            country_id=payload.country_id,
        )
        if existing is not None:
            raise DuplicateBand(f"Band {existing.id} already covers this {scope} scope")

        band = self._bands.add(
            SalaryBand(
                department_id=payload.department_id,
                role_id=payload.role_id,
                level_id=payload.level_id,
                country_id=payload.country_id,
                currency_code=currency,
                min_amount=payload.min_amount,
                mid_amount=payload.mid_amount,
                max_amount=payload.max_amount,
            )
        )
        self._uow.commit()
        return self.get_band(band.id)

    def update_band(self, band_id: int, payload: BandUpdate) -> BandOut:
        band = self._bands.get(band_id)
        if band is None:
            raise BandNotFound(f"Band {band_id} not found")
        changes = payload.model_dump(exclude_none=True)
        _check_amounts(
            changes.get("min_amount", band.min_amount),
            changes.get("mid_amount", band.mid_amount),
            changes.get("max_amount", band.max_amount),
        )
        for field, value in changes.items():
            setattr(band, field, value)
        self._uow.commit()
        return self.get_band(band_id)

    def delete_band(self, band_id: int) -> None:
        band = self._bands.get(band_id)
        if band is None:
            raise BandNotFound(f"Band {band_id} not found")
        if self._bands.is_referenced(band_id):
            # Salary history links the band it was priced against; keep that audit trail.
            raise BandInUse(f"Band {band_id} is linked to salary records; edit it instead")
        self._bands.delete(band)
        self._uow.commit()

    def _check_scope(self, payload: BandCreate) -> str:
        """Validate the band's references; returns the currency it is priced in."""
        if not self._references.department_exists(payload.department_id):
            raise InvalidReference(f"Department {payload.department_id} does not exist")
        if not self._references.level_exists(payload.level_id):
            raise InvalidReference(f"Level {payload.level_id} does not exist")
        if payload.role_id is not None:
            role_department = self._references.role_department_id(payload.role_id)
            if role_department is None:
                raise InvalidReference(f"Role {payload.role_id} does not exist")
            if role_department != payload.department_id:
                raise InvalidReference(
                    f"Role {payload.role_id} does not belong to department {payload.department_id}"
                )
        if payload.country_id is None:
            return FALLBACK_BAND_CURRENCY
        currency = self._references.country_currency(payload.country_id)
        if currency is None:
            raise InvalidReference(f"Country {payload.country_id} does not exist")
        return currency


def _check_amounts(min_amount: Decimal, mid_amount: Decimal, max_amount: Decimal) -> None:
    if not min_amount <= mid_amount <= max_amount:
        raise InvalidBand(
            f"Band amounts must satisfy min <= mid <= max "
            f"(got {min_amount} / {mid_amount} / {max_amount})"
        )
