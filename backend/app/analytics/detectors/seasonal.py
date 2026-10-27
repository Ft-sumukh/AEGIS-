"""Seasonal diurnal and day-of-week anomaly detector."""

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class SeasonalDetector(BaseDetector):
    """Detects deviations from hour-of-day and day-of-week historical seasonal profiles."""

    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        anomalies: list[RawAnomaly] = []
        metric_cfg = config.get_metric_config(series.metric_name)

        for point in series.points:
            # Calculate seasonal baseline for same day-of-week and hour-of-day
            baseline = baseline_engine.calculate_seasonal_weekly_baseline(
                series=series,
                target_timestamp=point.timestamp,
                lookback_days=45,
            )

            if not baseline.is_valid:
                continue

            diff = point.value - baseline.expected_value
            # Allow wider tolerance for seasonal noise (3.0 std dev)
            tolerance = max(1e-5, baseline.standard_deviation * 3.0)

            is_anomaly = False
            if metric_cfg.is_higher_worse and diff > tolerance:
                is_anomaly = True
            elif (not metric_cfg.is_higher_worse) and diff < -tolerance:
                is_anomaly = True

            if is_anomaly:
                weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                day_name = weekday_names[point.timestamp.weekday()]
                hour_str = f"{point.timestamp.hour:02d}:00 UTC"

                ratio = point.value / max(1e-5, baseline.expected_value)
                explanation = (
                    f"{series.metric_name} observed at {point.value:.4f} {series.unit}, displaying an abnormal "
                    f"seasonal deviation ({ratio:.1f}× expected) compared to historical {day_name} {hour_str} "
                    f"profile baseline of {baseline.expected_value:.4f} ± {tolerance:.4f}."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=point.timestamp,
                        observed_value=point.value,
                        expected_value=baseline.expected_value,
                        deviation=diff,
                        detector_type=DetectorType.SEASONAL,
                        confidence=0.82,
                        explanation=explanation,
                        metadata={
                            "seasonal_expected": round(baseline.expected_value, 4),
                            "seasonal_std_dev": round(baseline.standard_deviation, 4),
                            "day_of_week": day_name,
                            "hour": point.timestamp.hour,
                            "baseline_type": baseline.baseline_type,
                        },
                        metric_id=point.metric_id,
                    )
                )

        return anomalies
