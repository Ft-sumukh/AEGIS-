"""Statistical validation and causal progression tests for injected operational incidents."""

from datetime import UTC, datetime, timedelta

import pytest

from app.generator.config import GeneratorConfig
from app.generator.synthesizer import EnterpriseDataSynthesizer


@pytest.fixture(scope="module")
def incident_dataset():
    """Generates dataset containing the incident window (Day 60) for analysis."""
    config = GeneratorConfig(
        days=65,
        customer_count=200,
        seed=42,
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
    )
    syn = EnterpriseDataSynthesizer(config)
    return syn.synthesize()


def test_incident_causal_progression(incident_dataset) -> None:
    """Verifies that deployment v4.8.2 strictly precedes operational metric degradation."""
    deployments = incident_dataset.deployments
    bad_deployment = next(
        (d for d in deployments if d["service"] == "checkout-service" and d["version"] == "v4.8.2"),
        None,
    )
    assert bad_deployment is not None
    dep_time = datetime.fromisoformat(bad_deployment["deployed_at"])

    # Verify incident system events exist and are chronologically ordered
    events = incident_dataset.system_events
    dep_event = next(
        e for e in events if e["event_type"] == "DEPLOYMENT_STARTED" and "v4.8.2" in e["message"]
    )
    db_warn = next(e for e in events if e["event_type"] == "DATABASE_WARNING")
    db_err = next(e for e in events if e["event_type"] == "DATABASE_ERROR")
    chk_fail = next(e for e in events if e["event_type"] == "CHECKOUT_FAILURE")

    t_dep = datetime.fromisoformat(dep_event["timestamp"])
    t_warn = datetime.fromisoformat(db_warn["timestamp"])
    t_err = datetime.fromisoformat(db_err["timestamp"])
    t_chk = datetime.fromisoformat(chk_fail["timestamp"])

    assert dep_time <= t_dep <= t_warn < t_err <= t_chk


def test_incident_statistical_degradation(incident_dataset) -> None:
    """Verifies statistical degradation during the incident window compared to pre-incident baseline."""
    metrics = incident_dataset.metrics
    target_day = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=60)

    pre_errors = []
    pre_latency = []
    pre_checkout_fails = []
    pre_revenue = []

    inc_errors = []
    inc_latency = []
    inc_checkout_fails = []
    inc_revenue = []

    for m in metrics:
        dt = datetime.fromisoformat(m["timestamp"])
        val = m["value"]

        # Pre-incident baseline: Day 59 same daytime hours (10:00 - 13:00)
        if dt.date() == (target_day - timedelta(days=1)).date() and (10 <= dt.hour <= 13):
            if m["metric_name"] == "api_error_rate":
                pre_errors.append(val)
            elif m["metric_name"] == "api_latency":
                pre_latency.append(val)
            elif m["metric_name"] == "checkout_failure_rate":
                pre_checkout_fails.append(val)
            elif m["metric_name"] == "revenue":
                pre_revenue.append(val)

        # Incident peak window: Day 60 daytime hours (10:00 - 13:00)
        elif dt.date() == target_day.date() and (10 <= dt.hour <= 13):
            if m["metric_name"] == "api_error_rate":
                inc_errors.append(val)
            elif m["metric_name"] == "api_latency":
                inc_latency.append(val)
            elif m["metric_name"] == "checkout_failure_rate":
                inc_checkout_fails.append(val)
            elif m["metric_name"] == "revenue":
                inc_revenue.append(val)

    avg_pre_err = sum(pre_errors) / len(pre_errors)
    avg_inc_err = sum(inc_errors) / len(inc_errors)

    avg_pre_lat = sum(pre_latency) / len(pre_latency)
    avg_inc_lat = sum(inc_latency) / len(inc_latency)

    avg_pre_chk = sum(pre_checkout_fails) / len(pre_checkout_fails)
    avg_inc_chk = sum(inc_checkout_fails) / len(inc_checkout_fails)

    avg_pre_rev = sum(pre_revenue) / len(pre_revenue)
    avg_inc_rev = sum(inc_revenue) / len(inc_revenue)

    # 1. API error rate increases by > 10x baseline
    assert avg_inc_err > 10.0 * avg_pre_err
    assert avg_inc_err > 0.10  # > 10%

    # 2. Latency increases by > 4x baseline
    assert avg_inc_lat > 4.0 * avg_pre_lat
    assert avg_inc_lat > 600.0  # > 600ms

    # 3. Checkout failure rate surges > 10x baseline
    assert avg_inc_chk > 10.0 * avg_pre_chk
    assert avg_inc_chk > 0.20  # > 20%

    # 4. Revenue drops by > 50%
    assert avg_inc_rev < 0.50 * avg_pre_rev


def test_incident_recovery(incident_dataset) -> None:
    """Verifies that operational metrics return toward normal baseline after rollback and recovery."""
    metrics = incident_dataset.metrics
    target_day = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=60)

    post_errors = []
    post_latency = []
    post_checkout_fails = []

    for m in metrics:
        dt = datetime.fromisoformat(m["timestamp"])
        # Post-recovery: Day 60 evening (19:00 - 22:00)
        if dt.date() == target_day.date() and (19 <= dt.hour <= 22):
            if m["metric_name"] == "api_error_rate":
                post_errors.append(m["value"])
            elif m["metric_name"] == "api_latency":
                post_latency.append(m["value"])
            elif m["metric_name"] == "checkout_failure_rate":
                post_checkout_fails.append(m["value"])

    avg_post_err = sum(post_errors) / len(post_errors)
    avg_post_lat = sum(post_latency) / len(post_latency)
    avg_post_chk = sum(post_checkout_fails) / len(post_checkout_fails)

    # Metrics have normalized
    assert avg_post_err < 0.01  # Under 1% error rate
    assert avg_post_lat < 180.0  # Under 180ms latency
    assert avg_post_chk < 0.025  # Under 2.5% checkout failures


def test_secondary_harmless_anomalies(incident_dataset) -> None:
    """Verifies that secondary anomalies do not manifest catastrophic error rates or false incidents."""
    metrics = incident_dataset.metrics
    mkt_day = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=22)

    mkt_traffic = []
    mkt_errors = []

    for m in metrics:
        dt = datetime.fromisoformat(m["timestamp"])
        if dt.date() == mkt_day.date() and (12 <= dt.hour <= 16):
            if m["metric_name"] == "traffic":
                mkt_traffic.append(m["value"])
            elif m["metric_name"] == "api_error_rate":
                mkt_errors.append(m["value"])

    # High traffic on marketing day
    assert len(mkt_traffic) > 0
    assert sum(mkt_traffic) / len(mkt_traffic) > 15000

    # But error rate remains low and healthy (< 0.5%)
    assert len(mkt_errors) > 0
    assert sum(mkt_errors) / len(mkt_errors) < 0.005
