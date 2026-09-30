"""Integration fixtures: a real MySQL schema, migrated from scratch once per run.

Each test runs inside a transaction that is rolled back afterwards. Service-level
commits become SAVEPOINT releases (join_transaction_mode="create_savepoint"), so
tests exercise the real commit path without leaking rows into each other.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, make_url
from sqlalchemy.orm import Session

from alembic import command
from app.core.database import connect_args
from app.core.dependencies import get_db
from app.core.settings import get_settings
from app.main import create_app

BACKEND_DIR = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    # Read through the app's settings, so it can come from backend/.env or the environment.
    url = get_settings().test_database_url
    if not url:
        pytest.skip("APP_TEST_DATABASE_URL not set; see backend/README.md")
    # These tests drop and recreate every table. Refuse anything that is not
    # obviously a throwaway database, so they can never wipe the real data.
    database = make_url(url).database or ""
    if not database.endswith("_test"):
        pytest.exit(
            f"APP_TEST_DATABASE_URL points at '{database}'; integration tests only run "
            "against a database whose name ends in '_test'",
            returncode=2,
        )

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    # Down then up, so every run also proves the migration is reversible.
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url, connect_args=connect_args())
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(engine: Engine) -> Iterator[Session]:
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False,
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
