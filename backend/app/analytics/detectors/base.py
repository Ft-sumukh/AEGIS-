"""Abstract base detector interface."""

from abc import ABC, abstractmethod

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.models import MetricSeries, RawAnomaly


class BaseDetector(ABC):
    """Abstract interface that all deterministic anomaly detectors implement."""

    @abstractmethod
    def detect(
        self,
        series: MetricSeries,
        baseline_engine: BaselineEngine,
        config: AnalyticsConfig,
    ) -> list[RawAnomaly]:
        """Scans the metric series and returns detected raw anomalies."""
        pass
