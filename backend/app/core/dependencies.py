"""FastAPI dependency providers. Service factories (get_*_service) are added here
as each service is built; tests override get_db or a service factory."""

from collections.abc import Callable, Iterator
from datetime import date
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import SqlAlchemyUnitOfWork, UnitOfWork, get_session_factory
from app.repository.band import SalaryBandRepository
from app.repository.employee import EmployeeRepository
from app.repository.reference import ReferenceRepository
from app.repository.salary import SalaryRepository
from app.services.band import BandResolver, BandService
from app.services.employee import EmployeeService
from app.services.salary import SalaryService


def get_db() -> Iterator[Session]:
    """One session per request.

    This never commits. Services commit explicitly through the UnitOfWork, so a write
    is durable before the response goes out, not in dependency teardown after it.
    Anything left uncommitted (e.g. after an exception) is rolled back on close.
    """
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_today() -> Callable[[], date]:
    """The clock services use for "today". Tests override this with a fixed date."""
    return date.today


def get_employee_service(session: DbSession) -> EmployeeService:
    return EmployeeService(
        employees=EmployeeRepository(session),
        references=ReferenceRepository(session),
        salaries=SalaryRepository(session),
        bands=BandResolver(SalaryBandRepository(session)),
        uow=SqlAlchemyUnitOfWork(session),
    )


EmployeeServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]


def get_salary_service(
    session: DbSession, today: Annotated[Callable[[], date], Depends(get_today)]
) -> SalaryService:
    return SalaryService(
        employees=EmployeeRepository(session),
        references=ReferenceRepository(session),
        salaries=SalaryRepository(session),
        bands=BandResolver(SalaryBandRepository(session)),
        uow=SqlAlchemyUnitOfWork(session),
        today=today,
    )


SalaryServiceDep = Annotated[SalaryService, Depends(get_salary_service)]


def get_band_service(session: DbSession) -> BandService:
    return BandService(
        bands=SalaryBandRepository(session),
        references=ReferenceRepository(session),
        uow=SqlAlchemyUnitOfWork(session),
    )


BandServiceDep = Annotated[BandService, Depends(get_band_service)]
