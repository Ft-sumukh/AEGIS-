"""Centralized configuration and metric importance registry for the analytics engine."""

from dataclasses import dataclass, field


@dataclass
class MetricThresholdConfig:
    """Thresholds, weights, and directional expectations for a specific metric."""

    importance: float = 0.5
    warning_threshold_high: float | None = None
    critical_threshold_high: float | None = None
    warning_threshold_low: float | None = None
    critical_threshold_low: float | None = None
    percentage_change_increase_threshold: float = 1.0  # +100%
    percentage_change_decrease_threshold: float = -0.5  # -50%
    is_higher_worse: bool = True  # True for errors/latency, False for revenue/conversion


@dataclass
class AnalyticsConfig:
    """Master configuration for the Operations Intelligence Engine."""

    # Z-score thresholds
    zscore_mild: float = 2.0
    zscore_significant: float = 3.0
    zscore_severe: float = 4.0

    # Rolling window sizes (hours)
    rolling_window_hours: int = 24
    minimum_baseline_samples: int = 6

    # Trend detection
    trend_window_hours: int = 6
    trend_min_consecutive: int = 3
    trend_slope_significance: float = 0.05

    # Multi-metric correlation parameters
    correlation_window_minutes: int = 75  # Anomalies within 75 mins can correlate
    min_correlation_score: float = 0.55  # Minimum score to cluster into IncidentCandidate
    correlation_weights: dict[str, float] = field(
        default_factory=lambda: {
            "temporal": 0.35,
            "dependency": 0.35,
            "direction": 0.15,
            "severity": 0.15,
        }
    )

    # Operational Dependency Graph (upstream -> downstream symptoms)
    dependency_graph: dict[str, list[str]] = field(
        default_factory=lambda: {
            "api_latency": ["api_error_rate", "checkout_failure_rate"],
            "api_error_rate": ["checkout_failure_rate", "failed_orders"],
            "checkout_failure_rate": ["failed_orders", "customer_complaint_count"],
            "failed_orders": ["customer_complaint_count", "support_ticket_count", "revenue"],
            "customer_complaint_count": ["support_ticket_count"],
            "support_ticket_count": ["revenue"],
            "orders": ["revenue"],
            "traffic": ["active_users", "orders"],
            "active_users": ["orders"],
            "conversion_rate": ["revenue", "orders"],
        }
    )

    # Metric-specific configuration registry
    metric_configs: dict[str, MetricThresholdConfig] = field(
        default_factory=lambda: {
            "checkout_failure_rate": MetricThresholdConfig(
                importance=1.0,
                warning_threshold_high=0.06,  # 6%
                critical_threshold_high=0.18,  # 18%
                percentage_change_increase_threshold=0.80,  # +80%
                is_higher_worse=True,
            ),
            "revenue": MetricThresholdConfig(
                importance=1.0,
                warning_threshold_low=None,
                critical_threshold_low=None,
                percentage_change_decrease_threshold=-0.45,  # -45%
                is_higher_worse=False,
            ),
            "order_completion_rate": MetricThresholdConfig(
                importance=0.90,
                warning_threshold_low=0.95,
                critical_threshold_low=0.85,
                percentage_change_decrease_threshold=-0.20,
                is_higher_worse=False,
            ),
            "api_error_rate": MetricThresholdConfig(
                importance=0.95,
                warning_threshold_high=0.03,  # 3%
                critical_threshold_high=0.08,  # 8%
                percentage_change_increase_threshold=1.5,  # +150%
                is_higher_worse=True,
            ),
            "failed_orders": MetricThresholdConfig(
                importance=0.85,
                warning_threshold_high=20.0,
                critical_threshold_high=60.0,
                percentage_change_increase_threshold=1.2,
                is_higher_worse=True,
            ),
            "api_latency": MetricThresholdConfig(
                importance=0.80,
                warning_threshold_high=350.0,  # 350ms
                critical_threshold_high=700.0,  # 700ms
                percentage_change_increase_threshold=0.75,  # +75%
                is_higher_worse=True,
            ),
            "customer_complaint_count": MetricThresholdConfig(
                importance=0.75,
                warning_threshold_high=8.0,
                critical_threshold_high=20.0,
                percentage_change_increase_threshold=1.5,
                is_higher_worse=True,
            ),
            "support_ticket_count": MetricThresholdConfig(
                importance=0.70,
                warning_threshold_high=15.0,
                critical_threshold_high=35.0,
                percentage_change_increase_threshold=1.5,
                is_higher_worse=True,
            ),
            "conversion_rate": MetricThresholdConfig(
                importance=0.65,
                warning_threshold_low=0.018,
                critical_threshold_low=0.010,
                percentage_change_decrease_threshold=-0.40,
                is_higher_worse=False,
            ),
            "orders": MetricThresholdConfig(
                importance=0.60,
                percentage_change_decrease_threshold=-0.45,
                is_higher_worse=False,
            ),
            "active_users": MetricThresholdConfig(
                importance=0.45,
                percentage_change_decrease_threshold=-0.50,
                is_higher_worse=False,
            ),
            "traffic": MetricThresholdConfig(
                importance=0.35,
                percentage_change_decrease_threshold=-0.50,
                is_higher_worse=False,
            ),
            "average_resolution_time": MetricThresholdConfig(
                importance=0.40,
                warning_threshold_high=90.0,
                critical_threshold_high=150.0,
                is_higher_worse=True,
            ),
        }
    )

    def get_metric_config(self, metric_name: str) -> MetricThresholdConfig:
        """Returns configuration for a given metric or a sensible default."""
        return self.metric_configs.get(metric_name, MetricThresholdConfig())
