"""Service layer for querying and filtering operational metrics."""

import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.metrics import OperationalMetric


class MetricsService:
    """Encapsulates database operations for operational metrics."""

    @staticmethod
    def list_metrics(
        db: Session,
        company_id: uuid.UUID | None = None,
        metric_name: str | None = None,
        start_time: datetime.datetime | None = None,
        end_time: datetime.datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[OperationalMetric], int]:
        """Query operational metrics with time-window filtering and pagination."""
        query = select(OperationalMetric)
        count_query = select(func.count(OperationalMetric.id))

        if company_id:
            query = query.where(OperationalMetric.company_id == company_id)
            count_query = count_query.where(OperationalMetric.company_id == company_id)

        if metric_name:
            query = query.where(OperationalMetric.metric_name == metric_name)
            count_query = count_query.where(OperationalMetric.metric_name == metric_name)

        if start_time:
            query = query.where(OperationalMetric.timestamp >= start_time)
            count_query = count_query.where(OperationalMetric.timestamp >= start_time)

        if end_time:
            query = query.where(OperationalMetric.timestamp <= end_time)
            count_query = count_query.where(OperationalMetric.timestamp <= end_time)

        total = db.scalar(count_query) or 0
        items = db.scalars(
            query.order_by(OperationalMetric.timestamp.desc()).limit(limit).offset(offset)
        ).all()

        return list(items), total
