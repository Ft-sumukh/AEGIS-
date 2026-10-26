"""Unit and integration tests for synthetic enterprise data generator."""

from datetime import UTC, datetime

import pytest

from app.generator.config import GeneratorConfig
from app.generator.synthesizer import EnterpriseDataSynthesizer


@pytest.fixture
def sample_config() -> GeneratorConfig:
    """Provides a lightweight 5-day test configuration."""
    return GeneratorConfig(
        company_name="NovaCart",
        days=5,
        customer_count=100,
        seed=42,
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
    )


def test_generator_reproducibility(sample_config: GeneratorConfig) -> None:
    """Verifies that running generator twice with the exact same seed produces identical outputs."""
    syn1 = EnterpriseDataSynthesizer(sample_config)
    ds1 = syn1.synthesize()

    syn2 = EnterpriseDataSynthesizer(sample_config)
    ds2 = syn2.synthesize()

    assert len(ds1.metrics) == len(ds2.metrics)
    assert len(ds1.orders) == len(ds2.orders)
    assert len(ds1.customers) == len(ds2.customers)

    # Check metric values match precisely
    for m1, m2 in zip(ds1.metrics[:50], ds2.metrics[:50], strict=True):
        assert m1["metric_name"] == m2["metric_name"]
        assert m1["timestamp"] == m2["timestamp"]
        assert m1["value"] == m2["value"]


def test_generator_time_horizon_and_metrics(sample_config: GeneratorConfig) -> None:
    """Verifies that the generator covers the full timeline and all 12 operational metrics."""
    syn = EnterpriseDataSynthesizer(sample_config)
    ds = syn.synthesize()

    expected_metric_names = {
        "traffic",
        "active_users",
        "orders",
        "failed_orders",
        "checkout_failure_rate",
        "api_error_rate",
        "api_latency",
        "revenue",
        "conversion_rate",
        "support_ticket_count",
        "customer_complaint_count",
        "average_resolution_time",
    }

    generated_metric_names = {m["metric_name"] for m in ds.metrics}
    assert expected_metric_names.issubset(generated_metric_names)

    # Hourly resolution: 5 days * 24 = 120 hours. With 12 metrics, ~1440 data points (minus 0.3% missing flaws)
    expected_hours = sample_config.days * 24
    assert len(ds.metrics) >= (expected_hours * 11)


def test_generator_diurnal_seasonality(sample_config: GeneratorConfig) -> None:
    """Verifies that daytime traffic is significantly higher than overnight traffic."""
    syn = EnterpriseDataSynthesizer(sample_config)
    ds = syn.synthesize()

    night_traffic = []
    day_traffic = []

    for m in ds.metrics:
        if m["metric_name"] == "traffic":
            dt = datetime.fromisoformat(m["timestamp"])
            if dt.hour in (1, 2, 3, 4):
                night_traffic.append(m["value"])
            elif dt.hour in (13, 14, 15, 16):
                day_traffic.append(m["value"])

    assert len(night_traffic) > 0
    assert len(day_traffic) > 0

    avg_night = sum(night_traffic) / len(night_traffic)
    avg_day = sum(day_traffic) / len(day_traffic)

    # Daytime traffic should be at least 2.5x overnight traffic
    assert avg_day > 2.5 * avg_night


def test_generator_causal_relationships(sample_config: GeneratorConfig) -> None:
    """Verifies that orders and revenue are causally correlated."""
    syn = EnterpriseDataSynthesizer(sample_config)
    ds = syn.synthesize()

    orders_by_time = {
        m["timestamp"]: m["value"] for m in ds.metrics if m["metric_name"] == "orders"
    }
    revenue_by_time = {
        m["timestamp"]: m["value"] for m in ds.metrics if m["metric_name"] == "revenue"
    }

    common_ts = set(orders_by_time.keys()) & set(revenue_by_time.keys())
    assert len(common_ts) > 50

    # Ensure zero orders corresponds to near-zero revenue
    for ts in list(common_ts)[:30]:
        order_count = orders_by_time[ts]
        rev = revenue_by_time[ts]
        if order_count > 0:
            assert rev > 0


def test_generator_privacy_compliance(sample_config: GeneratorConfig) -> None:
    """Verifies data minimization and privacy standards: no real emails or phones."""
    syn = EnterpriseDataSynthesizer(sample_config)
    ds = syn.synthesize()

    for cust in ds.customers:
        assert cust["email"].endswith("@example.com")
        assert cust["phone"].startswith("+1-555-")
        assert cust["external_reference"].startswith("CUST-")
