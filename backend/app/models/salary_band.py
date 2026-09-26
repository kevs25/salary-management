from decimal import Decimal

from sqlalchemy import CHAR, CheckConstraint, Computed, ForeignKey, Index, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SalaryBand(TimestampMixin, Base):
    """The org's pay policy for a (department, role, level, country) cell.

    role_id and country_id are nullable because band resolution falls back from
    dept+role+level+country, to dept+level+country (role NULL), to dept+level
    (role and country NULL). A band without a country is priced in USD.

    MySQL unique indexes treat NULLs as distinct, so a plain unique key on the four
    FKs would allow duplicate fallback bands. role_key/country_key map NULL to 0 and
    carry the uniqueness instead. The index leads with department and level, which
    every resolution strategy filters on.
    """

    __tablename__ = "salary_bands"
    __table_args__ = (
        Index(
            "uq_salary_bands_scope",
            "department_id",
            "level_id",
            "role_key",
            "country_key",
            unique=True,
        ),
        CheckConstraint(
            "min_amount >= 0 AND min_amount <= mid_amount AND mid_amount <= max_amount",
            name="min_mid_max_ordered",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    role_id: Mapped[int | None] = mapped_column(ForeignKey("job_roles.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    country_id: Mapped[int | None] = mapped_column(ForeignKey("countries.id"))
    currency_code: Mapped[str] = mapped_column(CHAR(3))
    min_amount: Mapped[Decimal]
    mid_amount: Mapped[Decimal]
    max_amount: Mapped[Decimal]

    role_key: Mapped[int] = mapped_column(
        SmallInteger, Computed("COALESCE(role_id, 0)", persisted=True)
    )
    country_key: Mapped[int] = mapped_column(
        SmallInteger, Computed("COALESCE(country_id, 0)", persisted=True)
    )
