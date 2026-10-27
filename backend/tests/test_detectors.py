"""Unit tests for the 6 modular anomaly detectors and baseline engine edge cases."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors import (
    PercentageChangeDetector,
    RollingBaselineDetector,
    SeasonalDetector,
    ThresholdDetector,
    TrendDetector,
    ZScoreDetector,
)
from app.analytics.models import MetricPoint, MetricSeries
from app.models.enums import DetectorType


@pytest.fixture
def test_company_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def baseline_engine() -> BaselineEngine:
    return BaselineEngine(min_samples=5)


@pytest.fixture
def analytics_config() -> AnalyticsConfig:
    return AnalyticsConfig(minimum_baseline_samples=5)


# ---------------------------------------------------------------------------
# 1. ThresholdDetector Tests
# ---------------------------------------------------------------------------
def test_threshold_detector_critical_breach(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """ThresholdDetector triggers when observed value exceeds critical upper limit."""
    detector = ThresholdDetector()
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    series = MetricSeries(
        company_id=test_company_id, metric_name="checkout_failure_rate", unit="ratio"
    )
    # Critical threshold for checkout_failure_rate in config is 0.18
    series.points = [
        MetricPoint(timestamp=t0, value=0.01),
        MetricPoint(timestamp=t0 + timedelta(minutes=5), value=0.02),
        MetricPoint(timestamp=t0 + timedelta(minutes=10), value=0.25),  # Breach > 0.18
    ]

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 1
    anom = anomalies[0]
    assert anom.detector_type == DetectorType.THRESHOLD
    assert anom.observed_value == 0.25
    assert anom.metadata["bound_type"] == "critical_high"


def test_threshold_detector_normal_value(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """ThresholdDetector ignores observations within normal operational thresholds."""
    detector = ThresholdDetector()
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    series = MetricSeries(
        company_id=test_company_id, metric_name="checkout_failure_rate", unit="ratio"
    )
    series.points = [MetricPoint(timestamp=t0 + timedelta(minutes=i), value=0.01) for i in range(5)]

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 0


def test_threshold_detector_lower_breach(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """ThresholdDetector detects metric dropping below critical minimum threshold."""
    detector = ThresholdDetector()
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    series = MetricSeries(
        company_id=test_company_id, metric_name="order_completion_rate", unit="ratio"
    )
    # order_completion_rate critical low threshold is 0.85
    series.points = [
        MetricPoint(timestamp=t0, value=0.98),
        MetricPoint(timestamp=t0 + timedelta(minutes=5), value=0.70),  # Drop < 0.85
    ]

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 1
    assert anomalies[0].metadata["bound_type"] == "critical_low"


# ---------------------------------------------------------------------------
# 2. PercentageChangeDetector Tests
# ---------------------------------------------------------------------------
def test_percentage_change_surge(test_company_id, baseline_engine, analytics_config) -> None:
    """PercentageChangeDetector flags rapid multi-fold surges."""
    detector = PercentageChangeDetector()
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    series = MetricSeries(company_id=test_company_id, metric_name="api_latency", unit="ms")
    # api_latency percentage_change_increase_threshold is 0.75 (+75%)
    series.points = [
        MetricPoint(timestamp=t0, value=100.0),
        MetricPoint(timestamp=t0 + timedelta(minutes=1), value=105.0),
        MetricPoint(timestamp=t0 + timedelta(minutes=2), value=450.0),  # > 300% jump
    ]

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 1
    assert anomalies[0].detector_type == DetectorType.PERCENTAGE_CHANGE
    assert anomalies[0].observed_value == 450.0
    assert anomalies[0].deviation > 300.0
    assert anomalies[0].metadata["jump_type"] == "surge"


def test_percentage_change_collapse(test_company_id, baseline_engine, analytics_config) -> None:
    """PercentageChangeDetector flags sudden steep drop in revenue."""
    detector = PercentageChangeDetector()
    t0 = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)

    series = MetricSeries(company_id=test_company_id, metric_name="revenue", unit="USD")
    # revenue percentage_change_decrease_threshold is -0.45 (-45%)
    series.points = [
        MetricPoint(timestamp=t0, value=5000.0),
        MetricPoint(timestamp=t0 + timedelta(hours=1), value=1500.0),  # 70% drop
    ]

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 1
    assert anomalies[0].metadata["jump_type"] == "collapse"


# ---------------------------------------------------------------------------
# 3. ZScoreDetector Tests
# ---------------------------------------------------------------------------
def test_zscore_detector_tiered_scoring(test_company_id, baseline_engine, analytics_config) -> None:
    """ZScoreDetector properly identifies mild, significant, and severe deviations."""
    detector = ZScoreDetector()
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    # 30 baseline points around mean 100, std ~1
    points = [
        MetricPoint(timestamp=t0 + timedelta(hours=i), value=100.0 + (i % 3 - 1)) for i in range(30)
    ]
    # Severe spike (Z > 4.0)
    severe_time = t0 + timedelta(hours=31)
    points.append(MetricPoint(timestamp=severe_time, value=150.0))

    series = MetricSeries(
        company_id=test_company_id, metric_name="api_latency", unit="ms", points=points
    )
    anomalies = detector.detect(series, baseline_engine, analytics_config)

    assert len(anomalies) >= 1
    severe_anom = next(a for a in anomalies if a.timestamp == severe_time)
    assert severe_anom.metadata["z_tier"] == "severe"
    assert severe_anom.confidence >= 0.70


# ---------------------------------------------------------------------------
# 4. RollingBaselineDetector Tests (Strict Causality & No Lookahead)
# ---------------------------------------------------------------------------
def test_rolling_baseline_strict_causality(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """RollingBaselineDetector must only look at historical [t - W, t) and never look into the future."""
    detector = RollingBaselineDetector()
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    # 20 calm points at value 10.0
    points = [MetricPoint(timestamp=t0 + timedelta(hours=i), value=10.0) for i in range(20)]
    # Anomaly spike at t = 20 hours
    spike_time = t0 + timedelta(hours=20)
    points.append(MetricPoint(timestamp=spike_time, value=50.0))

    # Next 10 points after spike at value 100.0
    for i in range(21, 31):
        points.append(MetricPoint(timestamp=t0 + timedelta(hours=i), value=100.0))

    series = MetricSeries(
        company_id=test_company_id, metric_name="api_error_rate", unit="ratio", points=points
    )

    # Baseline at spike_time must reflect pre-spike mean (10.0), NOT future 100.0
    baseline = baseline_engine.calculate_rolling_baseline(series, spike_time, window_hours=10)
    assert baseline.is_valid
    assert pytest.approx(baseline.expected_value, rel=1e-2) == 10.0

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    spike_anom = next((a for a in anomalies if a.timestamp == spike_time), None)
    assert spike_anom is not None
    assert pytest.approx(spike_anom.expected_value, rel=1e-2) == 10.0


# ---------------------------------------------------------------------------
# 5. SeasonalDetector Tests (Diurnal & Day-of-Week)
# ---------------------------------------------------------------------------
def test_seasonal_detector_diurnal_deviation(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """SeasonalDetector compares observation against same-hour historical distribution."""
    detector = SeasonalDetector()
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)  # Monday 00:00

    points = []
    # 14 days of data: at 14:00 UTC value is always ~5000.0, at 03:00 UTC value is ~500.0
    for day in range(14):
        day_start = t0 + timedelta(days=day)
        points.append(MetricPoint(timestamp=day_start.replace(hour=3), value=500.0 + (day % 2)))
        points.append(MetricPoint(timestamp=day_start.replace(hour=14), value=5000.0 + (day % 2)))

    # On Day 14 at 14:00 UTC, unexpected crash in revenue to 300.0 (below tolerance)
    anom_time = (t0 + timedelta(days=14)).replace(hour=14)
    points.append(MetricPoint(timestamp=anom_time, value=300.0))

    series = MetricSeries(
        company_id=test_company_id, metric_name="revenue", unit="USD", points=points
    )
    series.sort_by_timestamp()

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) >= 1
    target = next((a for a in anomalies if a.timestamp == anom_time), None)
    assert target is not None
    assert target.detector_type == DetectorType.SEASONAL
    assert target.expected_value > 4000.0


# ---------------------------------------------------------------------------
# 6. TrendDetector Tests (Linear Regression Slope)
# ---------------------------------------------------------------------------
def test_trend_detector_sustained_drift(test_company_id, baseline_engine) -> None:
    """TrendDetector detects sustained upward drift over time."""
    detector = TrendDetector()
    cfg = AnalyticsConfig(trend_window_hours=6, trend_slope_significance=0.03)
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    # Clean linear upward drift over 10 hours: y = 10 + 2*i
    points = [
        MetricPoint(timestamp=t0 + timedelta(hours=i), value=10.0 + 2.0 * i) for i in range(10)
    ]
    series = MetricSeries(
        company_id=test_company_id, metric_name="api_latency", unit="ms", points=points
    )

    anomalies = detector.detect(series, baseline_engine, cfg)
    assert len(anomalies) >= 1
    last_anom = anomalies[-1]
    assert last_anom.detector_type == DetectorType.TREND
    assert last_anom.metadata["trend_direction"] == "increasing"
    assert last_anom.metadata["slope"] > 0


def test_trend_detector_flat_series(test_company_id, baseline_engine, analytics_config) -> None:
    """TrendDetector does not flag stable / flat metrics."""
    detector = TrendDetector()
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)

    points = [
        MetricPoint(timestamp=t0 + timedelta(hours=i), value=50.0 + (i % 2 - 0.5))
        for i in range(20)
    ]
    series = MetricSeries(
        company_id=test_company_id, metric_name="api_latency", unit="ms", points=points
    )

    anomalies = detector.detect(series, baseline_engine, analytics_config)
    assert len(anomalies) == 0


# ---------------------------------------------------------------------------
# 7. Edge Cases: Zero Variance, Insufficient Data, Gaps
# ---------------------------------------------------------------------------
def test_baseline_zero_variance_protection(test_company_id, baseline_engine) -> None:
    """Zero variance across points produces valid baseline with safe std_dev and no zero-division."""
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    points = [MetricPoint(timestamp=t0 + timedelta(hours=i), value=42.0) for i in range(10)]
    series = MetricSeries(
        company_id=test_company_id, metric_name="constant_metric", unit="raw", points=points
    )

    baseline = baseline_engine.calculate_rolling_baseline(
        series, t0 + timedelta(hours=9), window_hours=24
    )
    assert baseline.is_valid
    assert baseline.expected_value == 42.0
    assert baseline.standard_deviation <= 1e-6


def test_detectors_insufficient_baseline_data(
    test_company_id, baseline_engine, analytics_config
) -> None:
    """Detectors return empty list without crashing when fewer than min_samples exist."""
    t0 = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    # Only 2 points when min_samples is 5
    points = [
        MetricPoint(timestamp=t0, value=10.0),
        MetricPoint(timestamp=t0 + timedelta(minutes=1), value=12.0),
    ]
    series = MetricSeries(
        company_id=test_company_id, metric_name="api_latency", unit="ms", points=points
    )

    for det in [RollingBaselineDetector(), SeasonalDetector(), ZScoreDetector()]:
        anomalies = det.detect(series, baseline_engine, analytics_config)
        assert isinstance(anomalies, list)
        assert len(anomalies) == 0


def test_detectors_empty_series(test_company_id, baseline_engine, analytics_config) -> None:
    """All detectors safely handle an empty MetricSeries."""
    series = MetricSeries(company_id=test_company_id, metric_name="empty_metric", unit="count")
    for det in [
        ThresholdDetector(),
        PercentageChangeDetector(),
        ZScoreDetector(),
        RollingBaselineDetector(),
        SeasonalDetector(),
        TrendDetector(),
    ]:
        anomalies = det.detect(series, baseline_engine, analytics_config)
        assert anomalies == []
