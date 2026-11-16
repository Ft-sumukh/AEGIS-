"""Detection quality evaluation utility for benchmarking precision, recall, and F1."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from app.models.anomaly import Anomaly
from app.models.enums import SeverityLevel


@dataclass
class DetectionEvaluationReport:
    """Statistical evaluation metrics against synthetic ground truth."""

    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float
    ground_truth_incident_hours: int
    total_evaluated_observations: int

    def to_dict(self) -> dict:
        return {
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": round(self.precision, 4),
            "recall": round(self.recall, 4),
            "f1_score": round(self.f1_score, 4),
            "ground_truth_incident_hours": self.ground_truth_incident_hours,
            "total_evaluated_observations": self.total_evaluated_observations,
            "disclaimer": "Synthetic ground-truth benchmarks serve for deterministic testing and do not guarantee equivalent real-world field metrics.",
        }


class BenchmarkEvaluator:
    """Computes precision, recall, and F1 score of anomaly detectors against ground truth incident windows."""

    @staticmethod
    def evaluate(
        detected_anomalies: Sequence[Anomaly],
        total_observations: int,
        incident_start: datetime,
        incident_end: datetime,
        affected_metrics: set[str],
    ) -> DetectionEvaluationReport:
        """Calculates evaluation matrix based on whether detected anomalies fall within known incident windows."""
        tp = 0
        fp = 0

        # Known incident duration in hours
        incident_duration_hours = max(
            1, int(round((incident_end - incident_start).total_seconds() / 3600.0))
        )
        expected_incident_anomalies = incident_duration_hours * len(affected_metrics)

        seen_incident_metric_hours = set()

        for a in detected_anomalies:
            if a.metric_name not in affected_metrics:
                continue

            is_in_incident_time = incident_start <= a.detected_at <= incident_end

            if is_in_incident_time:
                tp += 1
                seen_incident_metric_hours.add(
                    (a.metric_name, a.detected_at.hour, a.detected_at.date())
                )
            else:
                # Flagged during normal baseline on affected metric outside incident window
                if a.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL):
                    fp += 1

        fn = max(0, expected_incident_anomalies - len(seen_incident_metric_hours))
        tn = max(0, total_observations - tp - fp - fn)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return DetectionEvaluationReport(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=precision,
            recall=recall,
            f1_score=f1,
            ground_truth_incident_hours=incident_duration_hours,
            total_evaluated_observations=total_observations,
        )
