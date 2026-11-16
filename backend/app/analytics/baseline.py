"""Baseline calculation engine for rolling, historical, diurnal, and weekly expectations."""

import statistics
from collections.abc import Sequence
from datetime import datetime, timedelta

from app.analytics.models import BaselineResult, MetricSeries


class BaselineEngine:
    """Calculates causally sound historical baselines without lookahead bias."""

    def __init__(self, min_samples: int = 6) -> None:
        self.min_samples = min_samples

    def calculate_rolling_baseline(
        self,
        series: MetricSeries,
        target_timestamp: datetime,
        window_hours: int = 24,
    ) -> BaselineResult:
        """Calculates rolling mean and standard deviation over historical window [T - window, T).

        CRITICAL: Never uses observations at or after target_timestamp to prevent future leakage.
        """
        window_start = target_timestamp - timedelta(hours=window_hours)
        historical_vals = [
            p.value for p in series.points if window_start <= p.timestamp < target_timestamp
        ]

        return self._compute_statistics(historical_vals, baseline_type=f"rolling_{window_hours}h")

    def calculate_seasonal_diurnal_baseline(
        self,
        series: MetricSeries,
        target_timestamp: datetime,
        lookback_days: int = 30,
    ) -> BaselineResult:
        """Calculates baseline for the same hour-of-day (0-23) over past historical days."""
        lookback_start = target_timestamp - timedelta(days=lookback_days)
        target_hour = target_timestamp.hour

        historical_vals = [
            p.value
            for p in series.points
            if lookback_start <= p.timestamp < target_timestamp and p.timestamp.hour == target_hour
        ]

        return self._compute_statistics(historical_vals, baseline_type="seasonal_diurnal")

    def calculate_seasonal_weekly_baseline(
        self,
        series: MetricSeries,
        target_timestamp: datetime,
        lookback_days: int = 45,
    ) -> BaselineResult:
        """Calculates baseline for the same day-of-week (0-6) and hour-of-day."""
        lookback_start = target_timestamp - timedelta(days=lookback_days)
        target_hour = target_timestamp.hour
        target_weekday = target_timestamp.weekday()

        historical_vals = [
            p.value
            for p in series.points
            if lookback_start <= p.timestamp < target_timestamp
            and p.timestamp.hour == target_hour
            and p.timestamp.weekday() == target_weekday
        ]

        # If strict same-weekday has too few samples, fallback to diurnal baseline
        if len(historical_vals) < self.min_samples:
            return self.calculate_seasonal_diurnal_baseline(series, target_timestamp, lookback_days)

        return self._compute_statistics(historical_vals, baseline_type="seasonal_weekly")

    def calculate_historical_baseline(
        self,
        series: MetricSeries,
        target_timestamp: datetime,
    ) -> BaselineResult:
        """Calculates all-time historical baseline up to target_timestamp."""
        historical_vals = [p.value for p in series.points if p.timestamp < target_timestamp]
        return self._compute_statistics(historical_vals, baseline_type="historical_all_time")

    def _compute_statistics(self, values: Sequence[float], baseline_type: str) -> BaselineResult:
        """Helper to compute mean, standard deviation, and median with safety checks."""
        n = len(values)
        if n < self.min_samples:
            return BaselineResult(
                expected_value=0.0,
                standard_deviation=0.0,
                sample_count=n,
                baseline_type=baseline_type,
                is_valid=False,
                error_reason="INSUFFICIENT_BASELINE",
            )

        mean_val = statistics.mean(values)
        if n > 1:
            try:
                std_val = statistics.stdev(values)
            except Exception:
                std_val = 0.0
        else:
            std_val = 0.0

        # Handle zero variance gracefully
        if std_val < 1e-7:
            std_val = 1e-7

        return BaselineResult(
            expected_value=mean_val,
            standard_deviation=std_val,
            sample_count=n,
            baseline_type=baseline_type,
            is_valid=True,
            error_reason=None,
        )
