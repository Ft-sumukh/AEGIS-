"""Service layer for querying and filtering detected anomalies."""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.anomaly import Anomaly
from app.models.enums import AnomalyStatus, SeverityLevel


class AnomalyService:
    """Encapsulates database operations for anomaly records."""

    @staticmethod
    def list_anomalies(
        db: Session,
        company_id: uuid.UUID | None = None,
        severity: SeverityLevel | None = None,
        status: AnomalyStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Anomaly], int]:
        """Query anomalies with severity/status filtering and pagination."""
        query = select(Anomaly)
        count_query = select(func.count(Anomaly.id))

        if company_id:
            query = query.where(Anomaly.company_id == company_id)
            count_query = count_query.where(Anomaly.company_id == company_id)

        if severity:
            query = query.where(Anomaly.severity == severity)
            count_query = count_query.where(Anomaly.severity == severity)

        if status:
            query = query.where(Anomaly.status == status)
            count_query = count_query.where(Anomaly.status == status)

        total = db.scalar(count_query) or 0
        items = db.scalars(
            query.order_by(Anomaly.detected_at.desc()).limit(limit).offset(offset)
        ).all()

        return list(items), total

    @staticmethod
    def get_by_id(db: Session, anomaly_id: uuid.UUID) -> Anomaly | None:
        """Fetch an anomaly by its unique identifier."""
        return db.scalar(select(Anomaly).where(Anomaly.id == anomaly_id))

    @staticmethod
    def get_summary(db: Session, company_id: uuid.UUID | None = None) -> dict[str, Any]:
        """Aggregate counts across severity, status, detector type, and top affected metrics."""
        count_stmt = select(func.count(Anomaly.id))
        if company_id:
            count_stmt = count_stmt.where(Anomaly.company_id == company_id)
        total = db.scalar(count_stmt) or 0

        # Group by severity
        sev_stmt = select(Anomaly.severity, func.count(Anomaly.id)).group_by(Anomaly.severity)
        if company_id:
            sev_stmt = sev_stmt.where(Anomaly.company_id == company_id)
        by_severity = {
            (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
            for row in db.execute(sev_stmt).all()
            if row[0] is not None
        }

        # Group by status
        stat_stmt = select(Anomaly.status, func.count(Anomaly.id)).group_by(Anomaly.status)
        if company_id:
            stat_stmt = stat_stmt.where(Anomaly.company_id == company_id)
        by_status = {
            (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
            for row in db.execute(stat_stmt).all()
            if row[0] is not None
        }

        # Group by detector type
        det_stmt = select(Anomaly.detector_type, func.count(Anomaly.id)).group_by(
            Anomaly.detector_type
        )
        if company_id:
            det_stmt = det_stmt.where(Anomaly.company_id == company_id)
        by_detector = {
            (row[0].value if hasattr(row[0], "value") else str(row[0])): row[1]
            for row in db.execute(det_stmt).all()
            if row[0] is not None
        }

        # Top 10 affected metrics
        met_stmt = (
            select(Anomaly.metric_name, func.count(Anomaly.id))
            .group_by(Anomaly.metric_name)
            .order_by(func.count(Anomaly.id).desc())
            .limit(10)
        )
        if company_id:
            met_stmt = met_stmt.where(Anomaly.company_id == company_id)
        top_metrics = {str(row[0]): row[1] for row in db.execute(met_stmt).all()}

        return {
            "total_anomalies": total,
            "by_severity": by_severity,
            "by_status": by_status,
            "by_detector_type": by_detector,
            "top_metrics": top_metrics,
        }
