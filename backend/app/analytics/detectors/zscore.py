"""Z-score statistical deviation anomaly detector."""

import math

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class ZScoreDetector(BaseDetector):
    """Detects statistical outliers using standardized z-scores against rolling historical baselines."""

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

            std_dev = baseline.standard_deviation
            if std_dev < 1e-7:
                continue

            diff = point.value - baseline.expected_value
            z = diff / std_dev

            # Check if direction is adverse
            is_anomaly = False
            z_tier = "mild"

            if metric_cfg.is_higher_worse and z >= config.zscore_mild:
                is_anomaly = True
            elif (not metric_cfg.is_higher_worse) and z <= -config.zscore_mild:
                is_anomaly = True

            if is_anomaly:
                abs_z = abs(z)
                if abs_z >= config.zscore_severe:
                    z_tier = "severe"
                elif abs_z >= config.zscore_significant:
                    z_tier = "significant"

                # Confidence scales with sample count and z magnitude
                confidence = min(0.98, 0.70 + 0.05 * math.log10(max(1, baseline.sample_count)))

                explanation = (
                    f"{series.metric_name} observed at {point.value:.4f} {series.unit}, displaying a {z_tier} "
                    f"z-score deviation of {z:+.2f}σ from the rolling expected mean of {baseline.expected_value:.4f} "
                    f"(std dev: {std_dev:.4f}, n={baseline.sample_count})."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=point.timestamp,
                        observed_value=point.value,
                        expected_value=baseline.expected_value,
                        deviation=diff,
                        detector_type=DetectorType.Z_SCORE,
                        confidence=confidence,
                        explanation=explanation,
                        metadata={
                            "z_score": round(z, 2),
                            "z_tier": z_tier,
                            "baseline_mean": round(baseline.expected_value, 4),
                            "baseline_std_dev": round(std_dev, 4),
                            "sample_count": baseline.sample_count,
                        },
                        metric_id=point.metric_id,
                    )
                )

        return anomalies
