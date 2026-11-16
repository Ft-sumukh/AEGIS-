"""Incident scenario abstraction and multi-phase degradation injection engine."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.generator.config import GeneratorConfig


@dataclass
class IncidentWindow:
    """Calculated start, peak, rollback, and recovery timestamps for an incident."""

    deployment_time: datetime
    latency_start: datetime
    error_start: datetime
    checkout_fail_start: datetime
    orders_fail_start: datetime
    complaints_start: datetime
    tickets_start: datetime
    revenue_impact_start: datetime
    peak_impact_time: datetime
    rollback_time: datetime
    recovery_end_time: datetime

    def is_in_incident_period(self, dt: datetime) -> bool:
        """Checks if timestamp falls within active degradation window."""
        return self.deployment_time <= dt <= self.recovery_end_time

    def get_degradation_factor(self, dt: datetime) -> float:
        """Computes smooth sigmoid/bell curve multiplier [0.0, 1.0] representing incident intensity.

        0.0 = baseline / no impact
        1.0 = peak catastrophic degradation
        """
        if dt < self.deployment_time or dt > self.recovery_end_time:
            return 0.0

        # Phase 1: Escalation (deployment_time -> peak_impact_time)
        if dt <= self.peak_impact_time:
            total_ramp = (self.peak_impact_time - self.deployment_time).total_seconds()
            if total_ramp <= 0:
                return 1.0
            elapsed = (dt - self.deployment_time).total_seconds()
            ratio = max(0.0, min(1.0, elapsed / total_ramp))
            # Smooth cubic ease-in
            return ratio * ratio * (3 - 2 * ratio)

        # Phase 2: Sustained peak until rollback
        if dt <= self.rollback_time:
            return 1.0

        # Phase 3: Post-rollback recovery (rollback_time -> recovery_end_time)
        recovery_duration = (self.recovery_end_time - self.rollback_time).total_seconds()
        if recovery_duration <= 0:
            return 0.0
        elapsed_recovery = (dt - self.rollback_time).total_seconds()
        ratio = max(0.0, min(1.0, elapsed_recovery / recovery_duration))
        # Smooth ease-out back to 0.0
        decay = 1.0 - ratio
        return decay * decay * (3 - 2 * decay)


@dataclass
class IncidentScenario:
    """Structured representation of an incident scenario for export and verification."""

    scenario_id: str
    title: str
    description: str
    affected_service: str
    root_cause: str
    deployment_version: str
    rollback_version: str
    timeline: list[dict[str, str]]
    impact_multipliers: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


class IncidentEngine:
    """Manages primary operational incident and secondary benign anomalies."""

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self.inc_cfg = config.incidents
        self.window = self._calculate_primary_window()

    def _calculate_primary_window(self) -> IncidentWindow:
        """Calculates exact timeline for the primary checkout API deployment incident."""
        start_date = self.config.start_date
        incident_day = start_date + timedelta(days=self.inc_cfg.primary_day_offset)

        # 09:14 UTC: deployment checkout-service v4.8.2
        dep_time = incident_day.replace(
            hour=self.inc_cfg.primary_start_hour,
            minute=self.inc_cfg.primary_start_minute,
            second=0,
            microsecond=0,
        )

        return IncidentWindow(
            deployment_time=dep_time,
            latency_start=dep_time + timedelta(minutes=6),  # 09:20
            error_start=dep_time + timedelta(minutes=11),  # 09:25
            checkout_fail_start=dep_time + timedelta(minutes=16),  # 09:30
            orders_fail_start=dep_time + timedelta(minutes=26),  # 09:40
            complaints_start=dep_time + timedelta(minutes=36),  # 09:50
            tickets_start=dep_time + timedelta(minutes=46),  # 10:00
            revenue_impact_start=dep_time + timedelta(minutes=61),  # 10:15
            peak_impact_time=dep_time + timedelta(hours=2, minutes=30),  # 11:44 (sustained peak)
            rollback_time=incident_day.replace(
                hour=self.inc_cfg.primary_rollback_hour, minute=0, second=0, microsecond=0
            ),  # 14:00 Rollback v4.8.1
            recovery_end_time=incident_day.replace(
                hour=self.inc_cfg.primary_recovery_hour, minute=0, second=0, microsecond=0
            ),  # 18:00 Full recovery
        )

    def get_scenario_metadata(self) -> IncidentScenario:
        """Constructs detailed metadata for incident_scenarios.json."""
        win = self.window
        return IncidentScenario(
            scenario_id="INC-20260731-001",
            title="Checkout API Database Connection Pool Exhaustion",
            description=(
                "Deployment v4.8.2 introduced misconfigured HikariCP connection pool settings "
                "(max_connections reduced to 5 with 30s timeout), causing thread starvation, "
                "cascading 504 Gateway Timeouts, 500 Internal Server Errors, checkout order failures, "
                "customer support escalations, and substantial revenue decline."
            ),
            affected_service="checkout-service",
            root_cause="HikariCP connection pool exhaustion in checkout-service v4.8.2 deployment",
            deployment_version="v4.8.2",
            rollback_version="v4.8.1",
            timeline=[
                {
                    "time": win.deployment_time.isoformat(),
                    "event": "Deployment v4.8.2 released to production by release-pipeline",
                },
                {
                    "time": win.latency_start.isoformat(),
                    "event": "checkout-service p95/p99 latency begins rapid increase",
                },
                {
                    "time": win.error_start.isoformat(),
                    "event": "API gateway logs surge in 504 Gateway Timeouts and 500 DB timeout errors",
                },
                {
                    "time": win.checkout_fail_start.isoformat(),
                    "event": "Checkout failure rate escalates from 1.2% to >25%",
                },
                {
                    "time": win.orders_fail_start.isoformat(),
                    "event": "Order processing worker fails with DB connection dropouts",
                },
                {
                    "time": win.complaints_start.isoformat(),
                    "event": "Customer complaints spike on failed payment processing",
                },
                {
                    "time": win.tickets_start.isoformat(),
                    "event": "Support ticket queue floods with critical checkout failure issues",
                },
                {
                    "time": win.revenue_impact_start.isoformat(),
                    "event": "Gross hourly order revenue drops by >70% compared to diurnal baseline",
                },
                {
                    "time": win.rollback_time.isoformat(),
                    "event": "SRE on-call executes emergency rollback to deployment v4.8.1",
                },
                {
                    "time": win.recovery_end_time.isoformat(),
                    "event": "Connection pools normalize, latency and error rates return to baseline",
                },
            ],
            impact_multipliers={
                "api_error_rate_peak": self.inc_cfg.api_error_rate_peak,
                "api_latency_ms_peak": self.inc_cfg.api_latency_ms_peak,
                "checkout_failure_rate_peak": self.inc_cfg.checkout_failure_rate_peak,
                "revenue_reduction_peak": self.inc_cfg.revenue_reduction_peak,
                "support_ticket_multiplier": self.inc_cfg.support_ticket_multiplier,
                "complaint_multiplier": self.inc_cfg.complaint_multiplier,
            },
            metadata={
                "start_date": win.deployment_time.isoformat(),
                "end_date": win.recovery_end_time.isoformat(),
                "duration_hours": (win.recovery_end_time - win.deployment_time).total_seconds()
                / 3600.0,
                "classification": self.config.data_classification,
            },
        )

    def is_secondary_marketing_spike(self, dt: datetime) -> bool:
        """Day 22: Marketing promotional campaign (high traffic, normal low errors)."""
        target_day = self.config.start_date + timedelta(days=self.inc_cfg.marketing_spike_day)
        return dt.date() == target_day.date() and (10 <= dt.hour <= 20)

    def is_secondary_network_blip(self, dt: datetime) -> bool:
        """Day 45: Transient 1-hour cloud ISP latency flutter (no errors, no dropped orders)."""
        target_day = self.config.start_date + timedelta(days=self.inc_cfg.network_blip_day)
        return dt.date() == target_day.date() and dt.hour == 14

    def is_secondary_weekend_promo(self, dt: datetime) -> bool:
        """Day 75: Flash sale weekend (healthy traffic & revenue increase, no incident)."""
        target_day = self.config.start_date + timedelta(days=self.inc_cfg.weekend_promo_day)
        return dt.date() == target_day.date() and (11 <= dt.hour <= 21)
