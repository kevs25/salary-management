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

    def fx_rate(self, currency_code: str) -> Decimal | None:
        stmt = select(FxRate.rate_to_usd).where(FxRate.currency_code == currency_code)
        return self.session.scalar(stmt)
