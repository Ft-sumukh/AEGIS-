"""Percentage change jump anomaly detector."""

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class PercentageChangeDetector(BaseDetector):
    """Detects sudden, dramatic percentage jumps or collapses compared to recent values."""

    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        anomalies: list[RawAnomaly] = []
        if len(series.points) < 2:
            return anomalies

        metric_cfg = config.get_metric_config(series.metric_name)
        inc_thresh = metric_cfg.percentage_change_increase_threshold
        dec_thresh = metric_cfg.percentage_change_decrease_threshold

        for i in range(1, len(series.points)):
            prev_point = series.points[i - 1]
            curr_point = series.points[i]

            prev_val = prev_point.value
            curr_val = curr_point.value

            # Avoid division by zero
            denom = abs(prev_val) if abs(prev_val) > 1e-5 else 1e-5
            pct_change = (curr_val - prev_val) / denom

            is_anomaly = False
            jump_type = ""

            # Adverse increase check
            if metric_cfg.is_higher_worse and pct_change >= inc_thresh:
                is_anomaly = True
                jump_type = "surge"
            # Adverse decrease check
            elif (not metric_cfg.is_higher_worse) and pct_change <= dec_thresh:
                is_anomaly = True
                jump_type = "collapse"

            if is_anomaly:
                pct_str = f"{pct_change * 100:+.1f}%"
                explanation = (
                    f"{series.metric_name} underwent a sudden {jump_type} of {pct_str} "
                    f"from {prev_val:.4f} to {curr_val:.4f} {series.unit} within 1 hour."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=curr_point.timestamp,
                        observed_value=curr_val,
                        expected_value=prev_val,
                        deviation=curr_val - prev_val,
                        detector_type=DetectorType.PERCENTAGE_CHANGE,
                        confidence=0.88,
                        explanation=explanation,
                        metadata={
                            "percentage_change": round(pct_change, 4),
                            "previous_value": prev_val,
                            "jump_type": jump_type,
                        },
                        metric_id=curr_point.metric_id,
                    )
                )

        return anomalies
