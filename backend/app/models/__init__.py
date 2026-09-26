"""Importing this package registers every table on Base.metadata (Alembic relies on it)."""

from app.models.base import Base
from app.models.employee import Employee, EmployeeStatus
from app.models.reference import Country, Department, FxRate, JobRole, Level
from app.models.salary_band import BandScope, SalaryBand
from app.models.salary_record import ChangeReason, SalaryRecord

__all__ = [
    "BandScope",
    "Base",
    "ChangeReason",
    "Country",
    "Department",
    "Employee",
    "EmployeeStatus",
    "FxRate",
    "JobRole",
    "Level",
    "SalaryBand",
    "SalaryRecord",
]
