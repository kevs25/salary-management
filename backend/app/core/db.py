from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_settings = get_settings()

# create_engine does not connect; the first query does.
engine = create_engine(
    _settings.database_url,
    echo=_settings.sql_echo,
    pool_pre_ping=True,
    pool_recycle=3600,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """One session per request.

    This never commits. Services commit explicitly through the UnitOfWork, so a write
    is durable before the response goes out, not in dependency teardown after it.
    Anything left uncommitted (e.g. after an exception) is rolled back on close.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
