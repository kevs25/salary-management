from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.exceptions import (
    BandInUse,
    BandNotFound,
    DuplicateBand,
    InvalidBand,
    InvalidReference,
)
from app.models import BandScope, Country, Department, JobRole, Level, SalaryBand
from app.schemas.band import BandCreate, BandUpdate
from app.services.band import BandService
from tests.unit.fakes import FakeBandRepository, FakeReferenceRepository, FakeUnitOfWork

ENGINEERING, SALES = 1, 2
BACKEND, ACCOUNT_EXEC = 10, 20
L3 = 3
INDIA = 1


class World:
    def __init__(self) -> None:
        self.references = FakeReferenceRepository()
        self.references.departments = {
            ENGINEERING: Department(id=ENGINEERING, name="Engineering"),
            SALES: Department(id=SALES, name="Sales"),
        }
        self.references.roles = {
            BACKEND: JobRole(id=BACKEND, name="Backend Engineer", department_id=ENGINEERING),
            ACCOUNT_EXEC: JobRole(id=ACCOUNT_EXEC, name="Account Executive", department_id=SALES),
        }
        self.references.levels = {
            L3: Level(id=L3, code="L3", name="Senior", rank=3, min_years=5, max_years=8)
        }
        self.references.countries = {
            INDIA: Country(id=INDIA, code="IN", name="India", currency_code="INR")
        }
        self.bands = FakeBandRepository(self.references)
        self.uow = FakeUnitOfWork()
        self.service = BandService(bands=self.bands, references=self.references, uow=self.uow)

    def create(self, **overrides: object):
        fields: dict[str, object] = {
            "department_id": ENGINEERING,
            "role_id": BACKEND,
            "level_id": L3,
            "country_id": INDIA,
            "min_amount": "2400000.00",
            "mid_amount": "3000000.00",
            "max_amount": "3600000.00",
        }
        fields.update(overrides)
        return self.service.create_band(BandCreate.model_validate(fields))


@pytest.fixture
def world() -> World:
    return World()


class TestCreate:
    def test_exact_band_is_priced_in_the_country_currency(self, world: World) -> None:
        band = world.create()

        assert band.scope is BandScope.EXACT
        assert band.currency_code == "INR"
        assert band.role is not None and band.role.name == "Backend Engineer"
        assert band.country is not None and band.country.code == "IN"
        assert band.mid_amount == Decimal("3000000.00")
        assert world.uow.commits == 1

    def test_department_level_country_band(self, world: World) -> None:
        band = world.create(role_id=None)

        assert band.scope is BandScope.DEPARTMENT_LEVEL_COUNTRY
        assert band.role is None
        assert band.currency_code == "INR"

    def test_department_wide_band_is_priced_in_usd(self, world: World) -> None:
        band = world.create(role_id=None, country_id=None)

        assert band.scope is BandScope.DEPARTMENT_LEVEL
        assert band.country is None
        assert band.currency_code == "USD"

    def test_role_without_country_is_not_a_resolvable_scope(self, world: World) -> None:
        with pytest.raises(InvalidBand, match="must also name a country"):
            world.create(country_id=None)
        assert world.bands.bands == {}

    def test_duplicate_scope_is_a_conflict(self, world: World) -> None:
        world.create(role_id=None, country_id=None)

        with pytest.raises(DuplicateBand):
            world.create(role_id=None, country_id=None, mid_amount="3100000.00")
        assert len(world.bands.bands) == 1
        assert world.uow.commits == 1

    def test_same_cell_at_a_different_scope_is_not_a_duplicate(self, world: World) -> None:
        world.create()
        world.create(role_id=None)
        world.create(role_id=None, country_id=None)

        assert len(world.bands.bands) == 3

    def test_role_from_another_department_is_rejected(self, world: World) -> None:
        with pytest.raises(InvalidReference, match="does not belong"):
            world.create(role_id=ACCOUNT_EXEC)

    @pytest.mark.parametrize(
        "overrides",
        [{"department_id": 99}, {"level_id": 99}, {"role_id": 99}, {"country_id": 99}],
    )
    def test_unknown_references_are_rejected(self, world: World, overrides: dict) -> None:
        with pytest.raises(InvalidReference):
            world.create(**overrides)

    @pytest.mark.parametrize(
        ("low", "mid", "high"),
        [("3000001", "3000000", "3600000"), ("2400000", "3600001", "3600000")],
    )
    def test_amounts_must_be_ordered(self, world: World, low: str, mid: str, high: str) -> None:
        with pytest.raises(InvalidBand, match="min <= mid <= max"):
            world.create(min_amount=low, mid_amount=mid, max_amount=high)

    def test_flat_band_with_equal_amounts_is_allowed(self, world: World) -> None:
        band = world.create(min_amount="100.00", mid_amount="100.00", max_amount="100.00")

        assert band.min_amount == band.max_amount


class TestUpdate:
    def test_changes_only_the_amounts_sent(self, world: World) -> None:
        band_id = world.create().id

        band = world.service.update_band(band_id, BandUpdate(mid_amount=Decimal("3100000.00")))

        assert band.mid_amount == Decimal("3100000.00")
        assert band.min_amount == Decimal("2400000.00")
        assert world.uow.commits == 2

    def test_merged_amounts_must_stay_ordered(self, world: World) -> None:
        band_id = world.create().id

        with pytest.raises(InvalidBand):
            world.service.update_band(band_id, BandUpdate(min_amount=Decimal("3500000.00")))
        assert world.bands.bands[band_id].min_amount == Decimal("2400000.00")
        assert world.uow.commits == 1

    def test_unknown_band(self, world: World) -> None:
        with pytest.raises(BandNotFound):
            world.service.update_band(404, BandUpdate(mid_amount=Decimal("1")))

    def test_empty_update_is_rejected_by_schema(self) -> None:
        with pytest.raises(ValidationError):
            BandUpdate()

    def test_scope_cannot_be_changed(self) -> None:
        with pytest.raises(ValidationError):
            BandUpdate.model_validate({"country_id": 2})


class TestDelete:
    def test_unused_band_is_deleted(self, world: World) -> None:
        band_id = world.create().id

        world.service.delete_band(band_id)

        assert world.bands.bands == {}
        assert world.uow.commits == 2

    def test_band_linked_to_salary_history_is_kept(self, world: World) -> None:
        band_id = world.create().id
        world.bands.referenced.add(band_id)

        with pytest.raises(BandInUse):
            world.service.delete_band(band_id)
        assert band_id in world.bands.bands

    def test_unknown_band(self, world: World) -> None:
        with pytest.raises(BandNotFound):
            world.service.delete_band(404)


class TestGet:
    def test_unknown_band(self, world: World) -> None:
        with pytest.raises(BandNotFound):
            world.service.get_band(404)


@pytest.mark.parametrize(
    ("role_id", "country_id", "scope"),
    [
        (1, 1, BandScope.EXACT),
        (None, 1, BandScope.DEPARTMENT_LEVEL_COUNTRY),
        (None, None, BandScope.DEPARTMENT_LEVEL),
        (1, None, None),
    ],
)
def test_band_scope_from_its_nullable_columns(
    role_id: int | None, country_id: int | None, scope: BandScope | None
) -> None:
    assert SalaryBand(role_id=role_id, country_id=country_id).scope is scope
