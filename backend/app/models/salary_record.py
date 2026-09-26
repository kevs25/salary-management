import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ChangeReason(enum.StrEnum):
    HIRE = "hire"
    PROMOTION = "promotion"
    MERIT = "merit"
    MARKET_ADJUSTMENT = "market_adjustment"
    CORRECTION = "correction"


class SalaryRecord(Base):
    """One effective-dated period of an employee's pay. Rows are never overwritten.

    Periods are half-open: [effective_from, effective_to). effective_to is NULL on
    the open, current record. A revision sets the previous record's effective_to to
    the new effective_from and clears its is_current flag, in the same transaction.

    Amounts are stored in local currency and in USD, using the snapshot rate that was
    applied at write time (kept in fx_rate_to_usd so the conversion is auditable).

    is_current is denormalised so the list view is one join, not a correlated
    subquery. current_employee_id backs the invariant in the database: it is the
    employee_id on the current row and NULL otherwise, and it is unique, so MySQL
    rejects a second current record for the same employee.

    History is never deleted: the employee FK has no cascade (MySQL also forbids
    CASCADE on a base column of a stored generated column). Leavers are
    status=terminated, not removed.
    """

    __tablename__ = "salary_records"
    __table_args__ = (
        Index(None, "is_current"),
        Index("uq_salary_records_current_employee_id", "current_employee_id", unique=True),
        CheckConstraint("base_amount >= 0 AND bonus_amount >= 0", name="amounts_non_negative"),
        CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from", name="period_ordered"
        ),
        CheckConstraint(
            "(is_current AND effective_to IS NULL)"
            " OR (NOT is_current AND effective_to IS NOT NULL)",
            name="current_is_open",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    band_id: Mapped[int | None] = mapped_column(ForeignKey("salary_bands.id"))

    currency_code: Mapped[str] = mapped_column(CHAR(3))
    base_amount: Mapped[Decimal]
    bonus_amount: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    fx_rate_to_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    base_amount_usd: Mapped[Decimal]
    bonus_amount_usd: Mapped[Decimal] = mapped_column(default=Decimal("0"))

    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean)
    current_employee_id: Mapped[int | None] = mapped_column(
        Integer, Computed("IF(is_current, employee_id, NULL)", persisted=True)
    )

    reason: Mapped[ChangeReason] = mapped_column(
        Enum(ChangeReason, values_callable=lambda e: [m.value for m in e])
    )
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


# Declared on the columns (not as text) so Alembic can compare it; a text("... DESC")
# element shows up as permanent false drift in `alembic check`.
Index(
    "uq_salary_records_employee_id_effective_from",
    SalaryRecord.employee_id,
    SalaryRecord.effective_from.desc(),
    unique=True,
)
