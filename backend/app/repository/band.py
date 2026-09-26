from sqlalchemy import ColumnElement, exists, func, select
from sqlalchemy.orm import contains_eager

from app.models import BandScope, Country, Department, JobRole, Level, SalaryBand, SalaryRecord
from app.repository.base import SqlAlchemyRepository
from app.schemas.band import BandQuery

_SCOPE_CONDITIONS: dict[BandScope, tuple[ColumnElement[bool], ...]] = {
    BandScope.EXACT: (SalaryBand.role_id.is_not(None), SalaryBand.country_id.is_not(None)),
    BandScope.DEPARTMENT_LEVEL_COUNTRY: (
        SalaryBand.role_id.is_(None),
        SalaryBand.country_id.is_not(None),
    ),
    BandScope.DEPARTMENT_LEVEL: (SalaryBand.role_id.is_(None), SalaryBand.country_id.is_(None)),
}


def _conditions(query: BandQuery) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    for column, value in (
        (SalaryBand.department_id, query.department_id),
        (SalaryBand.role_id, query.role_id),
        (SalaryBand.level_id, query.level_id),
        (SalaryBand.country_id, query.country_id),
    ):
        if value is not None:
            conditions.append(column == value)
    if query.scope is not None:
        conditions.extend(_SCOPE_CONDITIONS[query.scope])
    return conditions


class SalaryBandRepository(SqlAlchemyRepository[SalaryBand]):
    model = SalaryBand

    def find_band(
        self,
        *,
        department_id: int,
        level_id: int,
        role_id: int | None,
        country_id: int | None,
    ) -> SalaryBand | None:
        """The band defined for exactly this scope; None in role/country means "any".

        Matches on the generated role_key/country_key (NULL stored as 0), so the
        lookup is a single probe of the unique uq_salary_bands_scope index.
        """
        stmt = select(SalaryBand).where(
            SalaryBand.department_id == department_id,
            SalaryBand.level_id == level_id,
            SalaryBand.role_key == (role_id or 0),
            SalaryBand.country_key == (country_id or 0),
        )
        return self.session.scalars(stmt).one_or_none()

    def list(self, query: BandQuery) -> tuple[list[SalaryBand], int]:
        conditions = _conditions(query)
        total = self.session.scalar(select(func.count()).select_from(SalaryBand).where(*conditions))
        page = query.page_params
        # Fallback bands (NULL role/country) sort before the specific ones in a cell.
        stmt = (
            self._with_names()
            .where(*conditions)
            .order_by(Department.name, Level.rank, JobRole.name, Country.name, SalaryBand.id)
            .limit(page.limit)
            .offset(page.offset)
        )
        return list(self.session.scalars(stmt)), total or 0

    def get_detail(self, band_id: int) -> SalaryBand | None:
        stmt = (
            self._with_names()
            .where(SalaryBand.id == band_id)
            # refresh server-set columns (updated_at) on an object already in the session
            .execution_options(populate_existing=True)
        )
        return self.session.scalars(stmt).one_or_none()

    def is_referenced(self, band_id: int) -> bool:
        """Whether any salary record (current or historical) was priced against it."""
        return bool(self.session.scalar(select(exists().where(SalaryRecord.band_id == band_id))))

    def delete(self, band: SalaryBand) -> None:
        self.session.delete(band)
        self.session.flush()

    @staticmethod
    def _with_names():
        return (
            select(SalaryBand)
            .join(Department, Department.id == SalaryBand.department_id)
            .join(Level, Level.id == SalaryBand.level_id)
            .outerjoin(JobRole, JobRole.id == SalaryBand.role_id)
            .outerjoin(Country, Country.id == SalaryBand.country_id)
            .options(
                contains_eager(SalaryBand.department),
                contains_eager(SalaryBand.level),
                contains_eager(SalaryBand.role),
                contains_eager(SalaryBand.country),
            )
        )
