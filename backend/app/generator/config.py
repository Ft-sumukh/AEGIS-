"""Configuration module for synthetic enterprise data generation."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class IncidentConfig:
    """Configuration for injected operational incidents."""

    # Primary incident parameters (Checkout API degradation)
    primary_enabled: bool = True
    primary_day_offset: int = 60  # Day 60 of simulation
    primary_start_hour: int = 9  # 09:00 UTC
    primary_start_minute: int = 14  # 09:14 UTC deployment
    primary_rollback_hour: int = 14  # 14:00 UTC rollback deployment
    primary_recovery_hour: int = 18  # 18:00 UTC fully restored

    # Degraded multipliers during peak incident
    api_error_rate_peak: float = 0.165  # Baseline ~0.002 -> 16.5% peak
    api_latency_ms_peak: float = 920.0  # Baseline ~120ms -> 920ms peak
    checkout_failure_rate_peak: float = 0.52  # Baseline ~0.012 -> 52.0% peak
    revenue_reduction_peak: float = 0.72  # 72% drop in completed order revenue
    support_ticket_multiplier: float = 6.5  # 6.5x surge in tickets
    complaint_multiplier: float = 8.0  # 8.0x surge in complaints

    # Secondary harmless anomalies (no incident declared)
    marketing_spike_day: int = 22  # Day 22: Traffic surge, normal low error rate
    network_blip_day: int = 45  # Day 45: Transient 1-hr latency blip
    weekend_promo_day: int = 75  # Day 75: High weekend conversion spike

    # Controlled data quality flaws for validation testing
    missing_metric_probability: float = 0.003  # 0.3% missing metric observations
    duplicate_event_probability: float = 0.005  # 0.5% duplicate events
    malformed_metadata_probability: float = 0.004  # 0.4% nullable/unusual metadata


@dataclass
class GeneratorConfig:
    """Main configuration for synthetic enterprise dataset generation."""

    company_name: str = "NovaCart"
    company_industry: str = "E-commerce"
    company_description: str = "Synthetic high-volume omnichannel retail and e-commerce platform."

    # Temporal parameters
    start_date: datetime = field(default_factory=lambda: datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC))
    days: int = 90
    granularity_hours: int = 1
    seed: int = 42

    # Entity counts
    customer_count: int = 1500
    base_hourly_traffic: int = 12000
    base_conversion_rate: float = 0.032  # ~3.2% normal conversion
    base_average_order_value: float = 85.50  # USD

    # Output paths
    output_dir: Path = field(default_factory=lambda: Path("data/synthetic"))
    data_classification: str = "PUBLIC_DEMO"

    # Incident scenario parameters
    incidents: IncidentConfig = field(default_factory=IncidentConfig)

    @property
    def total_hours(self) -> int:
        """Total hours across the simulation period."""
        return self.days * 24
