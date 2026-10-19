"""Pytest fixtures and test environment configuration."""

import sqlite3
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 Ensure all models are registered on Base.metadata
from app.config import Settings, get_settings
from app.database.base import Base
from app.database.seed import seed_database
from app.database.session import get_db
from app.main import app as fastapi_app


def get_test_settings() -> Settings:
    """Test settings override."""
    return Settings(
        APP_NAME="AegisTest",
        APP_VERSION="0.2.0-test",
        ENVIRONMENT="test",
        LOG_LEVEL="DEBUG",
        DATABASE_URL="sqlite:///:memory:",
        API_V1_PREFIX="/api/v1",
        CORS_ORIGINS=["http://testserver"],
        AI_PROVIDER="mock",
        AI_MODEL="test-model",
    )


# Enforce SQLite foreign keys in unit testing
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: object, _connection_record: object) -> None:
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create in-memory SQLite engine for the test suite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Provide an isolated, transactional database session per test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = testing_session_local()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def seeded_db_session(db_session: Session) -> Session:
    """Provide a database session pre-populated with the coherent seed narrative."""
    seed_database(db_session)
    return db_session


@pytest.fixture(scope="function")
def client(seeded_db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI TestClient fixture with database and settings dependencies overridden."""

    def override_get_db() -> Generator[Session, None, None]:
        yield seeded_db_session

    fastapi_app.dependency_overrides[get_settings] = get_test_settings
    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()
