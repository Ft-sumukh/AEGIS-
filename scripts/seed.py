"""CLI wrapper script to seed the Aegis database."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_logging
from app.database.base import Base
from app.database.seed import seed_database
from app.database.session import get_engine, get_session_factory
import app.models  # noqa: F401 Ensure models are registered on Base

import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Aegis Database")
    parser.add_argument("--sqlite", action="store_true", help="Force SQLite database")
    parser.add_argument("--reset", action="store_true", help="Reset existing database before seeding")
    parser.add_argument("--db-url", type=str, default=None, help="Override database URL")
    args = parser.parse_args()

    setup_logging()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = args.db_url
    if args.sqlite:
        db_url = "sqlite:///./data/aegis_dev.db"
    elif not db_url:
        try:
            test_engine = get_engine()
            with test_engine.connect() as conn:
                pass
            engine = test_engine
            session_factory = get_session_factory()
        except Exception:
            db_url = "sqlite:///./data/aegis_dev.db"

    if db_url and db_url.startswith("sqlite"):
        Path("./data").mkdir(exist_ok=True)
        engine = create_engine(db_url)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    if args.reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with session_factory() as session:
        result = seed_database(session)
        print("\n>>> Aegis Seed Database Result:")
        for key, value in result.items():
            print(f"    {key}: {value}")
