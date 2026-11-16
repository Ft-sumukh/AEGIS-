"""Anomaly scoring, severity assignment, confidence calculation, and fingerprinting."""

import hashlib
import uuid

from app.analytics.config import AnalyticsConfig
from app.analytics.models import AnomalyScore, RawAnomaly
from app.models.enums import DetectorType, SeverityLevel


class AnomalyScorer:
    """Calculates defensible severity, statistical confidence, and unique fingerprints."""

    def __init__(self, config: AnalyticsConfig) -> None:
        self.config = config

    def score(
        self,
        raw: RawAnomaly,
        company_id: uuid.UUID,
    ) -> AnomalyScore:
        """Evaluates a raw anomaly and returns an AnomalyScore."""
        metric_cfg = self.config.get_metric_config(raw.metric_name)

        bound_type = raw.metadata.get("bound_type", "")
        z_tier = raw.metadata.get("z_tier", "")

        # 1. Base severity tier from detector semantics
        if "critical" in bound_type or z_tier == "severe":
            severity = SeverityLevel.CRITICAL
        elif "warning" in bound_type or z_tier == "significant":
            severity = SeverityLevel.HIGH
        elif z_tier == "mild":
            severity = SeverityLevel.MEDIUM
        elif raw.detector_type == DetectorType.PERCENTAGE_CHANGE:
            # Significant jump on high-importance metric
            val = raw.observed_value
            if (
                metric_cfg.critical_threshold_high is not None
                and val >= metric_cfg.critical_threshold_high
            ) or (
                metric_cfg.critical_threshold_low is not None
                and val <= metric_cfg.critical_threshold_low
            ):
                severity = SeverityLevel.CRITICAL
            elif (
                metric_cfg.warning_threshold_high is not None
                and val >= metric_cfg.warning_threshold_high
            ) or (
                metric_cfg.warning_threshold_low is not None
                and val <= metric_cfg.warning_threshold_low
            ):
                severity = SeverityLevel.HIGH
            elif metric_cfg.importance >= 0.8:
                severity = SeverityLevel.MEDIUM
            else:
                severity = SeverityLevel.LOW
        else:
            # Rolling / Seasonal / Trend: evaluate severity against configured threshold envelopes
            val = raw.observed_value
            if (
                metric_cfg.critical_threshold_high is not None
                and val >= metric_cfg.critical_threshold_high
            ):
                severity = SeverityLevel.CRITICAL
            elif (
                metric_cfg.warning_threshold_high is not None
                and val >= metric_cfg.warning_threshold_high
            ):
                severity = SeverityLevel.HIGH
            elif (
                metric_cfg.critical_threshold_low is not None
                and val <= metric_cfg.critical_threshold_low
            ):
                severity = SeverityLevel.CRITICAL
            elif (
                metric_cfg.warning_threshold_low is not None
                and val <= metric_cfg.warning_threshold_low
            ):
                severity = SeverityLevel.HIGH
            else:
                # Moderate deviation within safe operating envelope
                severity = SeverityLevel.LOW

        # Confidence: base confidence modulated by sample depth
        confidence = raw.confidence
        sample_count = raw.metadata.get("sample_count", 24)
        if sample_count < 6:
            confidence = max(0.50, confidence * 0.75)

        # Generate deterministic fingerprint: (company + metric + timestamp + detector)
        fp_str = (
            f"{company_id}:{raw.metric_name}:{raw.timestamp.isoformat()}:{raw.detector_type.value}"
        )
        fingerprint = hashlib.sha256(fp_str.encode("utf-8")).hexdigest()

        # Build explainability payload
        enriched_metadata = dict(raw.metadata)
        enriched_metadata.update(
            {
                "fingerprint": fingerprint,
                "metric_importance": metric_cfg.importance,
                "severity_level": severity.value,
            }
        )

        return AnomalyScore(
            severity=severity,
            confidence=round(confidence, 3),
            explanation=raw.explanation,
            fingerprint=fingerprint,
            metadata=enriched_metadata,
        )
