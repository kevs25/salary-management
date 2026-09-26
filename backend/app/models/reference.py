"""Reference data: the dimensions every employee and band is keyed on."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(CHAR(2), unique=True)  # ISO 3166-1 alpha-2
    name: Mapped[str] = mapped_column(String(64))
    currency_code: Mapped[str] = mapped_column(CHAR(3))  # ISO 4217


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)


class JobRole(Base):
    """A role belongs to exactly one department (e.g. Backend Engineer -> Engineering)."""

    __tablename__ = "job_roles"
    __table_args__ = (UniqueConstraint("department_id", "name"),)

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(64))


class Level(Base):
    """Experience level, L1-L5. max_years is NULL for the open-ended top level."""

    __tablename__ = "levels"
    __table_args__ = (
        CheckConstraint("max_years IS NULL OR max_years > min_years", name="years_range"),
    )

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    rank: Mapped[int] = mapped_column(SmallInteger, unique=True)
    min_years: Mapped[int] = mapped_column(SmallInteger)
    max_years: Mapped[int | None] = mapped_column(SmallInteger)


class FxRate(Base):
    """Committed snapshot rate, not a live feed, so USD figures are reproducible."""

    __tablename__ = "fx_rates"

    currency_code: Mapped[str] = mapped_column(CHAR(3), primary_key=True)
    rate_to_usd: Mapped[Decimal] = mapped_column(Numeric(18, 8))
    as_of: Mapped[date] = mapped_column(Date)
