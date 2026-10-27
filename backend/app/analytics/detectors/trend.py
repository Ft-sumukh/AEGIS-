"""Linear regression trend and gradual degradation anomaly detector."""

import statistics

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.detectors.base import BaseDetector
from app.analytics.models import MetricSeries, RawAnomaly
from app.models.enums import DetectorType


class TrendDetector(BaseDetector):
    """Detects persistent, progressive creeping trends over sliding windows using linear regression."""

    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        anomalies: list[RawAnomaly] = []
        w_size = config.trend_window_hours
        if len(series.points) < w_size:
            return anomalies

        metric_cfg = config.get_metric_config(series.metric_name)

        # Slide window across series points
        for i in range(w_size, len(series.points) + 1):
            sub_points = series.points[i - w_size : i]
            y_vals = [p.value for p in sub_points]
            x_vals = list(range(len(y_vals)))  # 0, 1, ..., w_size - 1

            x_mean = statistics.mean(x_vals)
            y_mean = statistics.mean(y_vals)

            num = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, y_vals, strict=True))
            denom = sum((x - x_mean) ** 2 for x in x_vals)
            if denom == 0:
                continue

            slope = num / denom
            # Normalize slope by mean to get percentage growth/decay per step
            norm_factor = abs(y_mean) if abs(y_mean) > 1e-4 else 1e-4
            relative_slope = slope / norm_factor

            direction = "increasing" if slope > 0 else ("decreasing" if slope < 0 else "flat")
            is_anomaly = False

            # Check if trend is adverse and strong (creeping latency, errors, connection leaks)
            if metric_cfg.is_higher_worse and relative_slope >= config.trend_slope_significance:
                is_anomaly = True

            if is_anomaly:
                curr_point = sub_points[-1]
                pct_str = f"{relative_slope * 100:+.1f}%/hr"
                explanation = (
                    f"{series.metric_name} is exhibiting a persistent adverse {direction} trend over the last "
                    f"{w_size} hours (slope: {slope:+.4f} {series.unit}/hr, {pct_str}), moving from "
                    f"{y_vals[0]:.4f} to {curr_point.value:.4f}."
                )

                anomalies.append(
                    RawAnomaly(
                        metric_name=series.metric_name,
                        timestamp=curr_point.timestamp,
                        observed_value=curr_point.value,
                        expected_value=y_vals[0],
                        deviation=curr_point.value - y_vals[0],
                        detector_type=DetectorType.TREND,
                        confidence=0.80,
                        explanation=explanation,
                        metadata={
                            "slope": round(slope, 4),
                            "relative_slope": round(relative_slope, 4),
                            "trend_direction": direction,
                            "window_size": w_size,
                        },
                        metric_id=curr_point.metric_id,
                    )
                )

        return anomalies
