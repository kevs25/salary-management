import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.reference import Country, Department, JobRole, Level


class EmployeeStatus(enum.StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    TERMINATED = "terminated"


class Employee(TimestampMixin, Base):
    """Who someone is and where they sit. Pay lives in SalaryRecord, not here."""

    __tablename__ = "employees"
    __table_args__ = (Index(None, "department_id", "country_id", "level_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(16), unique=True)
    first_name: Mapped[str] = mapped_column(String(64))
    last_name: Mapped[str] = mapped_column(String(64))
    email: Mapped[str] = mapped_column(String(128), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    role_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"))
    level_id: Mapped[int] = mapped_column(ForeignKey("levels.id"))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    hire_date: Mapped[date] = mapped_column(Date)
    status: Mapped[EmployeeStatus] = mapped_column(
        Enum(EmployeeStatus, values_callable=lambda e: [m.value for m in e]),
        default=EmployeeStatus.ACTIVE,
    )

    # lazy="raise": related rows must be loaded explicitly (joinedload), so an
    # accidental per-row lazy load fails loudly instead of becoming an N+1.
    department: Mapped[Department] = relationship(lazy="raise")
    role: Mapped[JobRole] = relationship(lazy="raise")
    level: Mapped[Level] = relationship(lazy="raise")
    country: Mapped[Country] = relationship(lazy="raise")
    manager: Mapped["Employee | None"] = relationship(remote_side=[id], lazy="raise")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
