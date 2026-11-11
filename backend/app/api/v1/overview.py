"""Operations intelligence overview API endpoint."""

import datetime
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.logging import get_logger
from app.database.session import get_db
from app.models.anomaly import Anomaly
from app.models.company import Company
from app.models.enums import AnomalyStatus, IncidentStatus, OrderStatus, SeverityLevel
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.metrics import OperationalMetric
from app.models.order import Order
from app.schemas.incident import IncidentRead
from app.schemas.investigation import InvestigationRead
from app.schemas.metrics import OperationalMetricRead
from app.schemas.overview import OverviewKpis, OverviewResponse

logger = get_logger("aegis.api.overview")
router = APIRouter(prefix="/overview", tags=["Operations Overview"])


@router.get(
    "",
    response_model=OverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated operations overview",
    description="Consolidates active incidents, business blast radius, operational health metrics, and latest AI investigation.",
)
def get_overview(
    company_id: uuid.UUID | None = Query(default=None, description="Filter by company UUID"),
    db: Session = Depends(get_db),
) -> OverviewResponse:
    """Consolidated operational posture for the main operator console."""
    try:
        # Resolve company
        comp = None
        if company_id:
            comp = db.get(Company, company_id)
        else:
            comp = db.scalar(select(Company).limit(1))
        company_name = comp.name if comp else "Acme Cloud Commerce"
        comp_id = comp.id if comp else None

        # 1. Incident metrics
        active_inc_q = select(Incident).where(Incident.status != IncidentStatus.CLOSED)
        if comp_id:
            active_inc_q = active_inc_q.where(Incident.company_id == comp_id)
        active_incidents = list(db.scalars(active_inc_q.order_by(Incident.detected_at.desc())).all())

        active_count = len(active_incidents)
        critical_count = sum(1 for inc in active_incidents if inc.severity == SeverityLevel.CRITICAL)

        # Revenue impact & affected systems
        rev_impact = float(sum(inc.estimated_revenue_impact or 0 for inc in active_incidents))
        systems_set: set[str] = set()
        for inc in active_incidents:
            if inc.affected_systems:
                systems_set.update(inc.affected_systems)
        affected_systems_count = len(systems_set)

        # 2. Anomaly metrics
        anom_q = select(func.count(Anomaly.id)).where(Anomaly.status != AnomalyStatus.DISMISSED)
        if comp_id:
            anom_q = anom_q.where(Anomaly.company_id == comp_id)
        active_anomalies_count = db.scalar(anom_q) or 0

        # 3. Failed orders
        order_q = select(func.count(Order.id)).where(Order.status == OrderStatus.FAILED)
        if comp_id:
            order_q = order_q.where(Order.company_id == comp_id)
        failed_orders = db.scalar(order_q) or 0

        # 4. Latest key metrics
        key_metric_names = ["api_error_rate", "checkout_failure_rate", "revenue", "active_users"]
        key_metrics: list[OperationalMetricRead] = []
        api_err_curr = 0.0
        checkout_fail_curr = 0.0

        for m_name in key_metric_names:
            mq = (
                select(OperationalMetric)
                .where(OperationalMetric.metric_name == m_name)
            )
            if comp_id:
                mq = mq.where(OperationalMetric.company_id == comp_id)
            latest_m = db.scalar(mq.order_by(OperationalMetric.timestamp.desc()).limit(1))
            if latest_m:
                key_metrics.append(OperationalMetricRead.model_validate(latest_m))
                if m_name == "api_error_rate":
                    api_err_curr = float(latest_m.value)
                elif m_name == "checkout_failure_rate":
                    checkout_fail_curr = float(latest_m.value)

        # 5. Latest investigation
        inv_q = (
            select(Investigation)
            .order_by(Investigation.started_at.desc())
            .options(
                selectinload(Investigation.hypotheses),
                selectinload(Investigation.recommendations),
            )
            .limit(1)
        )
        latest_inv_orm = db.scalar(inv_q)
        latest_inv = (
            InvestigationRead.model_validate(latest_inv_orm) if latest_inv_orm else None
        )

        # 6. Core systems summary
        core_services = [
            {"name": "checkout-service", "category": "service", "status": "DEGRADED" if "checkout-service" in systems_set else "HEALTHY", "latency_ms": 285.0 if "checkout-service" in systems_set else 42.0, "error_rate": checkout_fail_curr},
            {"name": "catalog-service", "category": "service", "status": "HEALTHY", "latency_ms": 18.0, "error_rate": 0.01},
            {"name": "auth-service", "category": "service", "status": "HEALTHY", "latency_ms": 12.0, "error_rate": 0.00},
            {"name": "payment-gateway", "category": "integration", "status": "HEALTHY", "latency_ms": 120.0, "error_rate": 0.02},
            {"name": "notification-service", "category": "service", "status": "HEALTHY", "latency_ms": 35.0, "error_rate": 0.00},
            {"name": "postgres-cluster", "category": "database", "status": "DEGRADED" if "postgres-cluster" in systems_set else "HEALTHY", "latency_ms": 45.0 if "postgres-cluster" in systems_set else 2.5, "error_rate": 0.0},
        ]

        kpis = OverviewKpis(
            active_incidents=active_count,
            critical_incidents=critical_count,
            active_anomalies=active_anomalies_count,
            affected_systems_count=affected_systems_count,
            estimated_revenue_impact=rev_impact,
            failed_orders_count=failed_orders,
            api_error_rate_current=api_err_curr,
            checkout_failure_rate_current=checkout_fail_curr,
        )

        return OverviewResponse(
            status="DEGRADED" if critical_count > 0 or active_count > 0 else "OPERATIONAL",
            environment="production",
            company_name=company_name,
            last_updated=datetime.datetime.now(datetime.UTC).isoformat(),
            kpis=kpis,
            recent_incidents=[IncidentRead.model_validate(inc) for inc in active_incidents[:5]],
            latest_investigation=latest_inv,
            key_metrics=key_metrics,
            systems_summary=core_services,
        )
    except Exception as exc:
        logger.exception(f"Error computing dashboard overview: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve operational overview.",
        ) from exc
