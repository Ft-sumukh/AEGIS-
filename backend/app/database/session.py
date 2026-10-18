"""SQLAlchemy engine, session maker, and FastAPI database dependency."""

import time
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger("aegis.database")


@lru_cache
def get_engine() -> Engine:
    """Create and cache the SQLAlchemy engine with connection pooling and pre-ping."""
    settings = get_settings()

    engine_kwargs: dict = {
        "pool_pre_ping": True,
        "echo": settings.LOG_LEVEL.upper() == "DEBUG",
    }

    # Only apply pool settings if not using SQLite in unit tests
    if not settings.DATABASE_URL.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": settings.DB_POOL_SIZE,
                "max_overflow": settings.DB_MAX_OVERFLOW,
                "pool_timeout": settings.DB_POOL_TIMEOUT,
            }
        )

    logger.info(
        f"Initializing database engine for {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'}"
    )
    return create_engine(settings.DATABASE_URL, **engine_kwargs)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Create and cache the sessionmaker factory."""
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides an isolated database session per request."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> tuple[bool, float, str | None]:
    """Verify database connectivity with a lightweight ping query.

    Returns:
        tuple[bool, float, str | None]: (is_healthy, latency_ms, error_detail)
    """
    engine = get_engine()
    start_time = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000
        return True, latency_ms, None
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.warning(f"Database readiness check failed: {exc}")
        return False, latency_ms, str(exc)
