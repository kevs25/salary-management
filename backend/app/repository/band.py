from sqlalchemy import select

from app.models import SalaryBand
from app.repository.base import SqlAlchemyRepository


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
