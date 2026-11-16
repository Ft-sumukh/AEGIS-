"""Rolling window historical baseline anomaly detector."""

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class RollingBaselineDetector(BaseDetector):
    """Detects deviations exceeding a configured multiple of rolling standard error without lookahead bias."""

    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        anomalies: list[RawAnomaly] = []
        metric_cfg = config.get_metric_config(series.metric_name)

        for point in series.points:
            baseline = baseline_engine.calculate_rolling_baseline(
                series=series,
                target_timestamp=point.timestamp,
                window_hours=config.rolling_window_hours,
            )

            if not baseline.is_valid:
                continue

            diff = point.value - baseline.expected_value
            tolerance = max(1e-5, baseline.standard_deviation * 2.5)

            is_anomaly = False
            if metric_cfg.is_higher_worse and diff > tolerance:
                is_anomaly = True
            elif (not metric_cfg.is_higher_worse) and diff < -tolerance:
                is_anomaly = True

            if is_anomaly:
                mult = abs(diff) / tolerance
                explanation = (
                    f"{series.metric_name} observed at {point.value:.4f} {series.unit}, exceeding the "
                    f"24-hour rolling baseline expectation of {baseline.expected_value:.4f} by {mult:.1f}× tolerance."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=point.timestamp,
                        observed_value=point.value,
                        expected_value=baseline.expected_value,
                        deviation=diff,
                        detector_type=DetectorType.ROLLING_BASELINE,
                        confidence=0.85,
                        explanation=explanation,
                        metadata={
                            "rolling_mean": round(baseline.expected_value, 4),
                            "rolling_std_dev": round(baseline.standard_deviation, 4),
                            "tolerance": round(tolerance, 4),
                            "window_hours": config.rolling_window_hours,
                        },
                        metric_id=point.metric_id,
                    )
                )

        return anomalies
