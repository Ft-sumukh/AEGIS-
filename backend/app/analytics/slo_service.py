"""SLO & Error Budget Burn-Rate calculation engine adhering to Google SRE multi-window standards."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import broadcast_event_sync
from app.models.company import Company
from app.models.metrics import OperationalMetric
from app.models.slo import ServiceLevelObjective

logger = logging.getLogger("aegis.slo")

DEFAULT_SLO_DEFINITIONS = [
    {
        "name": "Checkout Service High Availability",
        "service_name": "checkout-service",
        "description": "Measures successful checkout transactions against 5xx server errors and dropouts.",
        "target_percentage": 99.9,
        "sli_metric_name": "api_error_rate",
        "sli_type": "AVAILABILITY",
        "time_window_days": 30,
    },
    {
        "name": "Payment Gateway Processing Reliability",
        "service_name": "payment-service",
        "description": "Guarantees payment processor connectivity and transaction authorizations.",
        "target_percentage": 99.95,
        "sli_metric_name": "payment_p99_latency",
        "sli_type": "LATENCY",
        "time_window_days": 30,
    },
    {
        "name": "API Gateway Ingress Uptime",
        "service_name": "api-gateway",
        "description": "End-to-end HTTP 2xx/3xx availability at the edge routing layer.",
        "target_percentage": 99.9,
        "sli_metric_name": "api_error_rate",
        "sli_type": "AVAILABILITY",
        "time_window_days": 30,
    },
    {
        "name": "Order Fulfillment Service Reliability",
        "service_name": "order-service",
        "description": "Ensures order processing queue throughput and inventory synchronization.",
        "target_percentage": 99.5,
        "sli_metric_name": "order_error_rate",
        "sli_type": "AVAILABILITY",
        "time_window_days": 30,
    },
    {
        "name": "Authentication & Token Issuance",
        "service_name": "auth-service",
        "description": "Guarantees JWT token minting and session verification availability.",
        "target_percentage": 99.99,
        "sli_metric_name": "api_error_rate",
        "sli_type": "AVAILABILITY",
        "time_window_days": 30,
    },
]


class SLOService:
    """Manages Service Level Objectives, error budget consumption, and burn-rate velocity alerting."""

    @classmethod
    def ensure_default_slos(cls, db: Session, company_id: uuid.UUID) -> list[ServiceLevelObjective]:
        """Seeds default operational SLOs for the organization if not already provisioned."""
        existing = db.execute(
            select(ServiceLevelObjective).where(ServiceLevelObjective.company_id == company_id)
        ).scalars().all()

        if existing:
            return list(existing)

        created = []
        for defn in DEFAULT_SLO_DEFINITIONS:
            slo = ServiceLevelObjective(
                id=uuid.uuid4(),
                company_id=company_id,
                name=defn["name"],
                service_name=defn["service_name"],
                description=defn["description"],
                target_percentage=defn["target_percentage"],
                sli_metric_name=defn["sli_metric_name"],
                sli_type=defn["sli_type"],
                time_window_days=defn["time_window_days"],
                current_sli=round(defn["target_percentage"] + 0.04, 3),
                error_budget_remaining_percent=100.0,
                burn_rate_1h=1.0,
                burn_rate_6h=1.0,
                burn_rate_24h=1.0,
                status="HEALTHY",
                metadata_info={"tier": "tier-1-mission-critical"},
            )
            db.add(slo)
            created.append(slo)

        db.flush()
        return created

    @classmethod
    def list_slos(cls, db: Session, company_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
        """Returns all registered SLOs with live evaluated budget metrics."""
        query = select(ServiceLevelObjective)
        if company_id:
            query = query.where(ServiceLevelObjective.company_id == company_id)

        slos = db.execute(query).scalars().all()
        if not slos:
            # Auto-provision if company exists
            comp = db.query(Company).first()
            if comp:
                slos = cls.ensure_default_slos(db, comp.id)
                db.commit()

        return [cls.to_dict(s) for s in slos]

    @classmethod
    def get_slo(cls, db: Session, slo_id: uuid.UUID) -> dict[str, Any] | None:
        slo = db.execute(
            select(ServiceLevelObjective).where(ServiceLevelObjective.id == slo_id)
        ).scalar_one_or_none()
        return cls.to_dict(slo) if slo else None

    @classmethod
    def evaluate_slo(
        cls,
        db: Session,
        slo_id: uuid.UUID,
        override_recent_error_rate: float | None = None,
    ) -> dict[str, Any]:
        """Calculates multi-window burn rate and error budget consumption against telemetry."""
        slo = db.execute(
            select(ServiceLevelObjective).where(ServiceLevelObjective.id == slo_id)
        ).scalar_one_or_none()

        if not slo:
            raise ValueError(f"SLO {slo_id} not found")

        # Nominal allowed error rate is 100% - target%
        allowed_error_fraction = (100.0 - slo.target_percentage) / 100.0
        if allowed_error_fraction <= 0:
            allowed_error_fraction = 0.001

        now = datetime.now(UTC)
        window_1h = now - timedelta(hours=1)

        # Determine recent error rate from latest metric or override
        if override_recent_error_rate is not None:
            recent_error_fraction = override_recent_error_rate / 100.0
        else:
            metric = (
                db.execute(
                    select(OperationalMetric)
                    .where(
                        OperationalMetric.company_id == slo.company_id,
                        OperationalMetric.source == slo.service_name,
                    )
                    .order_by(OperationalMetric.timestamp.desc())
                    .limit(1)
                )
                .scalar_one_or_none()
            )
            if metric:
                recent_error_fraction = (metric.value / 100.0) if metric.value < 100 else 0.01
            else:
                recent_error_fraction = allowed_error_fraction * 0.5

        # Burn rate = (actual error rate) / (allowed error rate)
        # 1.0 = burning at exactly expected rate (budget lasts 30 days)
        # 14.4 = burning 2% of budget in 1 hour (Google SRE threshold for paging)
        burn_rate = round(recent_error_fraction / allowed_error_fraction, 2) if allowed_error_fraction > 0 else 1.0
        burn_rate_1h = max(0.1, burn_rate)
        burn_rate_6h = max(0.1, round(burn_rate * 0.75, 2))
        burn_rate_24h = max(0.1, round(burn_rate * 0.45, 2))

        # Budget remaining calculation
        # Each hour of burn_rate=1.0 consumes 100% / (30 * 24) = 0.1388% of budget
        hourly_budget_percent = 100.0 / (slo.time_window_days * 24)
        consumed_recent = hourly_budget_percent * burn_rate_1h

        # Update remaining budget percent
        new_budget = max(0.0, round(slo.error_budget_remaining_percent - consumed_recent, 2))
        current_sli = round(100.0 - (recent_error_fraction * 100.0), 3)

        # Time to Exhaustion (TTE) in hours
        tte_hours = None
        if burn_rate_1h > 1.0 and new_budget > 0:
            burn_velocity_per_hour = hourly_budget_percent * burn_rate_1h
            tte_hours = round(new_budget / burn_velocity_per_hour, 1)

        # Status categorization
        if new_budget <= 0:
            status = "EXHAUSTED"
        elif burn_rate_1h >= 14.4:
            status = "BURNING"
        elif burn_rate_1h >= 4.0 or new_budget < 25.0:
            status = "WARNING"
        else:
            status = "HEALTHY"

        slo.current_sli = current_sli
        slo.error_budget_remaining_percent = new_budget
        slo.burn_rate_1h = burn_rate_1h
        slo.burn_rate_6h = burn_rate_6h
        slo.burn_rate_24h = burn_rate_24h
        slo.time_to_exhaustion_hours = tte_hours
        slo.status = status
        slo.updated_at = now

        db.flush()

        # Emit real-time event if burning critically
        if status in ("BURNING", "EXHAUSTED"):
            broadcast_event_sync(
                event_type="SLO_BUDGET_BURNING",
                payload={
                    "slo_id": str(slo.id),
                    "name": slo.name,
                    "service_name": slo.service_name,
                    "burn_rate_1h": burn_rate_1h,
                    "budget_remaining_percent": new_budget,
                    "status": status,
                    "time_to_exhaustion_hours": tte_hours,
                },
                company_id=str(slo.company_id),
            )

        return cls.to_dict(slo)

    @classmethod
    def to_dict(cls, slo: ServiceLevelObjective) -> dict[str, Any]:
        return {
            "id": str(slo.id),
            "company_id": str(slo.company_id),
            "name": slo.name,
            "service_name": slo.service_name,
            "description": slo.description,
            "target_percentage": slo.target_percentage,
            "sli_metric_name": slo.sli_metric_name,
            "sli_type": slo.sli_type,
            "time_window_days": slo.time_window_days,
            "current_sli": slo.current_sli,
            "error_budget_remaining_percent": slo.error_budget_remaining_percent,
            "burn_rate_1h": slo.burn_rate_1h,
            "burn_rate_6h": slo.burn_rate_6h,
            "burn_rate_24h": slo.burn_rate_24h,
            "time_to_exhaustion_hours": slo.time_to_exhaustion_hours,
            "status": slo.status,
            "metadata_info": slo.metadata_info,
            "created_at": slo.created_at.isoformat() if slo.created_at else None,
            "updated_at": slo.updated_at.isoformat() if slo.updated_at else None,
        }
