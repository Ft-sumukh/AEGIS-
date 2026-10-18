"""SQLAlchemy 2.x declarative base and common metadata."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base declarative class for all future Aegis database models."""

    pass
