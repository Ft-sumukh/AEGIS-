"""Static and boundary threshold anomaly detector."""

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class ThresholdDetector(BaseDetector):
    """Detects violations of static warning/critical upper and lower boundaries."""

    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        anomalies: list[RawAnomaly] = []
        metric_cfg = config.get_metric_config(series.metric_name)

        # Skip if no static thresholds are configured for this metric
        has_high = (
            metric_cfg.warning_threshold_high is not None
            or metric_cfg.critical_threshold_high is not None
        )
        has_low = (
            metric_cfg.warning_threshold_low is not None
            or metric_cfg.critical_threshold_low is not None
        )
        if not (has_high or has_low):
            return anomalies

        for point in series.points:
            val = point.value
            breached = False
            threshold_val = 0.0
            bound_type = ""

            # Check Upper Boundaries
            if (
                metric_cfg.critical_threshold_high is not None
                and val >= metric_cfg.critical_threshold_high
            ):
                breached = True
                threshold_val = metric_cfg.critical_threshold_high
                bound_type = "critical_high"
            elif (
                metric_cfg.warning_threshold_high is not None
                and val >= metric_cfg.warning_threshold_high
            ):
                breached = True
                threshold_val = metric_cfg.warning_threshold_high
                bound_type = "warning_high"

            # Check Lower Boundaries
            elif (
                metric_cfg.critical_threshold_low is not None
                and val <= metric_cfg.critical_threshold_low
            ):
                breached = True
                threshold_val = metric_cfg.critical_threshold_low
                bound_type = "critical_low"
            elif (
                metric_cfg.warning_threshold_low is not None
                and val <= metric_cfg.warning_threshold_low
            ):
                breached = True
                threshold_val = metric_cfg.warning_threshold_low
                bound_type = "warning_low"

            if breached:
                deviation = val - threshold_val
                explanation = (
                    f"{series.metric_name} observed at {val:.4f} {series.unit}, breaching the configured "
                    f"{bound_type.replace('_', ' ')} threshold of {threshold_val:.4f} {series.unit}."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=point.timestamp,
                        observed_value=val,
                        expected_value=threshold_val,
                        deviation=deviation,
                        detector_type=DetectorType.THRESHOLD,
                        confidence=0.95,  # Static threshold breaches have very high certainty
                        explanation=explanation,
                        metadata={
                            "bound_type": bound_type,
                            "threshold_value": threshold_val,
                            "unit": series.unit,
                        },
                        metric_id=point.metric_id,
                    )
                )

        return anomalies
