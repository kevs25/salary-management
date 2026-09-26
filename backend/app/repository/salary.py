from decimal import Decimal

from sqlalchemy import select

from app.models import FxRate, SalaryRecord
from app.repository.base import SqlAlchemyRepository


class SalaryRepository(SqlAlchemyRepository[SalaryRecord]):
    model = SalaryRecord

    def history(self, employee_id: int) -> list[SalaryRecord]:
        """Every record for the employee, newest first (reads the history index in order)."""
        stmt = (
            select(SalaryRecord)
            .where(SalaryRecord.employee_id == employee_id)
            .order_by(SalaryRecord.effective_from.desc())
        )
        return list(self.session.scalars(stmt))

    def current_for_update(self, employee_id: int) -> SalaryRecord | None:
        """The employee's current record, row-locked until the transaction ends.

        Two concurrent revisions for one employee serialise here: the second waits
        for the first to commit. Whatever it then reads, the unique index on
        current_employee_id still guarantees at most one current record.
        """
        stmt = (
            select(SalaryRecord)
            .where(SalaryRecord.current_employee_id == employee_id)
            .with_for_update()
        )
        return self.session.scalars(stmt).one_or_none()

    def fx_rate(self, currency_code: str) -> Decimal | None:
        stmt = select(FxRate.rate_to_usd).where(FxRate.currency_code == currency_code)
        return self.session.scalar(stmt)
