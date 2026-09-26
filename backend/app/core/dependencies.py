"""FastAPI dependency providers. Service factories (get_*_service) are added here
as each service is built; tests override get_db or a service factory."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import SqlAlchemyUnitOfWork, UnitOfWork, get_session_factory


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
