"""Chaos Engineering and Controlled Operational Fault Injection Engine for Aegis."""

from datetime import UTC, datetime, timedelta
import logging
from typing import Any
import uuid

from sqlalchemy.orm import Session

from app.core.events import broadcast_event_sync
from app.models.company import Company
from app.models.enums import SeverityLevel
from app.models.events import Deployment, SystemEvent
from app.models.metrics import OperationalMetric

logger = logging.getLogger("aegis.chaos")

SCENARIOS: dict[str, dict[str, Any]] = {
    "LATENCY_SPIKE": {
        "id": "LATENCY_SPIKE",
        "name": "Payment Gateway Upstream Throttling",
        "description": "Simulates downstream processor timeout cascading into P99 latency spikes.",
        "target_service": "payment-service",
        "metric_name": "payment_p99_latency",
        "baseline_value": 115.0,
        "fault_value": 3450.0,
        "unit": "ms",
        "risk_level": "HIGH",
        "recommended_action": "ENABLE_FEATURE_FLAG",
        "action_params": {"flag_name": "circuit_breaker_payment_v2", "enabled": True},
    },
    "ERROR_BURST": {
        "id": "ERROR_BURST",
        "name": "Order Processing Connection Pool Starvation",
        "description": "Simulates database connection pool exhaustion resulting in widespread HTTP 500 errors.",
        "target_service": "order-service",
        "metric_name": "order_error_rate",
        "baseline_value": 0.12,
        "fault_value": 44.8,
        "unit": "%",
        "risk_level": "CRITICAL",
        "recommended_action": "RESTART_SERVICE",
        "action_params": {"service_name": "order-service", "graceful_timeout_sec": 30},
    },
    "CPU_SATURATION": {
        "id": "CPU_SATURATION",
        "name": "Inventory Service Reindexing CPU Saturation",
        "description": "Simulates CPU spike to 95%+ starving transaction processing threads.",
        "target_service": "inventory-service",
        "metric_name": "inventory_cpu_utilization",
        "baseline_value": 28.5,
        "fault_value": 96.2,
        "unit": "%",
        "risk_level": "MEDIUM",
        "recommended_action": "SCALE_SERVICE",
        "action_params": {"service_name": "inventory-service", "target_replicas": 8},
    },
    "CANARY_MEMORY_LEAK": {
        "id": "CANARY_MEMORY_LEAK",
        "name": "Authentication Token Session Memory Leak",
        "description": "Simulates a buggy canary release leaking memory over time.",
        "target_service": "auth-service",
        "metric_name": "auth_memory_usage_mb",
        "baseline_value": 420.0,
        "fault_value": 3850.0,
        "unit": "MB",
        "risk_level": "HIGH",
        "recommended_action": "ROLLBACK_DEPLOYMENT",
        "action_params": {"target_deployment_id": "dep-auth-stable-v1.9", "service_name": "auth-service"},
    },
}

# In-memory active simulations tracker
ACTIVE_CHAOS_RUNS: dict[str, dict[str, Any]] = {}


class ChaosEngine:
    """Manages active chaos experiments and fault injection against simulated infrastructure."""

    @classmethod
    def list_scenarios(cls) -> list[dict[str, Any]]:
        """Returns the catalog of available fault injection scenarios."""
        return list(SCENARIOS.values())

    @classmethod
    def get_scenario(cls, scenario_id: str) -> dict[str, Any] | None:
        return SCENARIOS.get(scenario_id.upper())

    @classmethod
    def get_active_simulations(cls) -> list[dict[str, Any]]:
        return list(ACTIVE_CHAOS_RUNS.values())

    @classmethod
    def inject_fault(
        cls,
        db: Session,
        scenario_id: str,
        actor: str = "operator",
    ) -> dict[str, Any]:
        """Injects a simulated operational fault, writing anomalous metrics and emitting live alerts."""
        scen = cls.get_scenario(scenario_id)
        if not scen:
            raise ValueError(f"Unknown chaos scenario '{scenario_id}'")

        company = db.query(Company).first()
        if not company:
            company = Company(id=uuid.uuid4(), name="Chaos Lab Corp", slug="chaos-corp")
            db.add(company)
            db.flush()

        now = datetime.now(UTC)
        run_id = f"CHAOS-{uuid.uuid4().hex[:8].upper()}"

        # 1. Insert anomalous metric
        metric = OperationalMetric(
            id=uuid.uuid4(),
            company_id=company.id,
            metric_name=scen["metric_name"],
            source=scen["target_service"],
            value=scen["fault_value"],
            unit=scen["unit"],
            timestamp=now,
            dimension_data={
                "environment": "production",
                "service": scen["target_service"],
                "chaos_run_id": run_id,
                "injected_by": actor,
            },
        )
        db.add(metric)

        # 2. Insert corresponding system event
        from app.models.enums import SeverityLevel

        event = SystemEvent(
            id=uuid.uuid4(),
            company_id=company.id,
            event_type="CHAOS_FAULT_INJECTED",
            service=scen["target_service"],
            environment="production",
            severity=SeverityLevel.HIGH if scen["risk_level"] in ("HIGH", "CRITICAL") else SeverityLevel.MEDIUM,
            message=f"Chaos experiment {scen['name']} initiated by {actor}.",
            source="chaos-engine",
            timestamp=now,
            event_metadata={
                "scenario_id": scen["id"],
                "run_id": run_id,
                "metric": scen["metric_name"],
                "injected_value": scen["fault_value"],
            },
        )
        db.add(event)
        db.commit()

        run_state = {
            "run_id": run_id,
            "scenario": scen,
            "injected_at": now.isoformat(),
            "injected_by": actor,
            "status": "ACTIVE_FAULT",
            "metric_id": str(metric.id),
        }
        ACTIVE_CHAOS_RUNS[run_id] = run_state

        # 3. Broadcast real-time SSE event
        broadcast_event_sync(
            event_type="CHAOS_FAULT_INJECTED",
            payload={
                "run_id": run_id,
                "scenario_id": scen["id"],
                "target_service": scen["target_service"],
                "fault_value": scen["fault_value"],
                "unit": scen["unit"],
                "injected_by": actor,
            },
            company_id=str(company.id),
        )

        logger.info(f"Chaos fault injected: {run_id} ({scen['name']}) by {actor}")
        return run_state

    @classmethod
    def recover_fault(
        cls,
        db: Session,
        run_id: str,
        actor: str = "operator",
    ) -> dict[str, Any]:
        """Restores baseline telemetry and completes the chaos experiment."""
        run_state = ACTIVE_CHAOS_RUNS.get(run_id)
        if not run_state:
            raise ValueError(f"Active chaos run '{run_id}' not found.")

        scen = run_state["scenario"]
        company = db.query(Company).first()
        company_id = company.id if company else uuid.uuid4()
        now = datetime.now(UTC)

        # 1. Insert restored baseline metric
        restored_metric = OperationalMetric(
            id=uuid.uuid4(),
            company_id=company_id,
            metric_name=scen["metric_name"],
            source=scen["target_service"],
            value=scen["baseline_value"],
            unit=scen["unit"],
            timestamp=now,
            dimension_data={
                "environment": "production",
                "service": scen["target_service"],
                "chaos_run_id": run_id,
                "recovered_by": actor,
            },
        )
        db.add(restored_metric)

        # 2. Insert system recovery event
        event = SystemEvent(
            id=uuid.uuid4(),
            company_id=company_id,
            event_type="CHAOS_FAULT_RECOVERED",
            service=scen["target_service"],
            environment="production",
            severity=SeverityLevel.INFO,
            message=f"Chaos experiment {scen['name']} recovered by {actor}.",
            source="chaos-engine",
            timestamp=now,
            event_metadata={
                "scenario_id": scen["id"],
                "run_id": run_id,
                "restored_value": scen["baseline_value"],
            },
        )
        db.add(event)
        db.commit()

        run_state["status"] = "RECOVERED"
        run_state["recovered_at"] = now.isoformat()
        run_state["recovered_by"] = actor

        # 3. Broadcast recovery event
        broadcast_event_sync(
            event_type="CHAOS_FAULT_RECOVERED",
            payload={
                "run_id": run_id,
                "scenario_id": scen["id"],
                "target_service": scen["target_service"],
                "restored_value": scen["baseline_value"],
                "recovered_by": actor,
            },
            company_id=str(company_id),
        )

        logger.info(f"Chaos fault recovered: {run_id} ({scen['name']}) by {actor}")
        return run_state
