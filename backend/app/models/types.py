"""Cross-dialect SQLAlchemy types supporting PostgreSQL and SQLite test environments."""

import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, TypeDecorator
from sqlalchemy.dialects import postgresql


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC DateTime type that ensures all timestamps are stored and loaded in UTC."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime.datetime | None, dialect: Any
    ) -> datetime.datetime | None:
        if value is not None:
            if value.tzinfo is None:
                # Assume UTC if naive, but ensure timezone is set
                value = value.replace(tzinfo=datetime.UTC)
            else:
                value = value.astimezone(datetime.UTC)
        return value

    def process_result_value(
        self, value: datetime.datetime | None, dialect: Any
    ) -> datetime.datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=datetime.UTC)
        return value


def PortableJSON() -> TypeDecorator:
    """Returns PostgreSQL JSONB when running on PostgreSQL, and standard JSON on other dialects."""
    return JSON().with_variant(postgresql.JSONB, "postgresql")
