from functools import lru_cache
from typing import Any, Protocol

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.settings import get_settings


def database_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("APP_DATABASE_URL is not set (see backend/.env.example)")
    return url


def connect_args() -> dict[str, Any]:
    """Driver arguments shared by the app, Alembic and the integration tests."""
    ca = get_settings().db_ssl_ca
    return {"ssl": {"ca": ca}} if ca else {}


@lru_cache
def get_engine() -> Engine:
    """The process-wide engine, created on first use.

    Lazy so that importing the app (e.g. in unit tests) never needs a database.
    create_engine does not connect either; the first query does.
    """
    settings = get_settings()
    return create_engine(
        database_url(),
        connect_args=connect_args(),
        poolclass=QueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_pre_ping=True,
        echo=settings.sql_echo,
    )


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


class UnitOfWork(Protocol):
    """Transaction boundary, as seen by services.

    Services take this instead of a Session so they stay free of SQLAlchemy and can
    be unit-tested with a fake that just records whether it was committed.
    """

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
