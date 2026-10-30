"""Deterministic multi-metric correlation engine and incident candidate clusterer."""

import uuid
from datetime import timedelta

from app.analytics.config import AnalyticsConfig
from app.analytics.models import IncidentCandidate
from app.models.anomaly import Anomaly
from app.models.enums import SeverityLevel


class MultiMetricCorrelator:
    """Correlates isolated metric anomalies using temporal proximity and operational dependency graphs."""

    def __init__(self, config: AnalyticsConfig) -> None:
        self.config = config

    def correlate(
        self,
        anomalies: list[Anomaly],
        company_id: uuid.UUID,
    ) -> list[IncidentCandidate]:
        """Clusters related anomalies into structured IncidentCandidate objects."""
        if not anomalies:
            return []

        # Sort chronologically
        sorted_anomalies = sorted(anomalies, key=lambda a: a.detected_at)
        clusters = self._cluster_temporally(sorted_anomalies)

        candidates: list[IncidentCandidate] = []
        for cluster in clusters:
            candidate = self._evaluate_cluster(cluster, company_id)
            if candidate is not None:
                candidates.append(candidate)

        return candidates

    def _cluster_temporally(self, anomalies: list[Anomaly]) -> list[list[Anomaly]]:
        """Groups anomalies into temporal clusters using sliding time window."""
        clusters: list[list[Anomaly]] = []
        window_delta = timedelta(minutes=self.config.correlation_window_minutes)

        current_cluster: list[Anomaly] = []
        for a in anomalies:
            if not current_cluster:
                current_cluster.append(a)
                continue

            # Compare against the first or latest element in the cluster
            if (a.detected_at - current_cluster[-1].detected_at) <= window_delta:
                current_cluster.append(a)
            else:
                clusters.append(current_cluster)
                current_cluster = [a]

        if current_cluster:
            clusters.append(current_cluster)

        return clusters

    def _evaluate_cluster(
        self,
        cluster: list[Anomaly],
        company_id: uuid.UUID,
    ) -> IncidentCandidate | None:
        """Scores a cluster and generates an IncidentCandidate if correlation criteria are met."""
        distinct_metrics = sorted({a.metric_name for a in cluster})
        # Require at least 2 distinct metrics to form a correlated multi-metric incident candidate
        if len(distinct_metrics) < 2:
            return None

        # 1. Temporal Proximity Score (how tight is the time spread)
        start_t = cluster[0].detected_at
        end_t = cluster[-1].detected_at
        spread_mins = max(1.0, (end_t - start_t).total_seconds() / 60.0)
        max_allowed = max(spread_mins, float(self.config.correlation_window_minutes))
        temporal_score = max(0.2, min(1.0, 1.0 - (spread_mins / (max_allowed * 2.0))))

        # 2. Dependency Graph Score
        dependency_score = self._compute_dependency_score(distinct_metrics)

        # 3. Directional Alignment Score
        direction_score = self._compute_directional_score(cluster)

        # 4. Severity Score
        sev_weights = {
            SeverityLevel.CRITICAL: 1.0,
            SeverityLevel.HIGH: 0.8,
            SeverityLevel.MEDIUM: 0.5,
            SeverityLevel.LOW: 0.2,
            SeverityLevel.INFO: 0.1,
            SeverityLevel.WARNING: 0.7,
            SeverityLevel.ERROR: 0.9,
        }
        avg_sev = sum(sev_weights.get(a.severity, 0.5) for a in cluster) / len(cluster)

        # Composite Correlation Score
        weights = self.config.correlation_weights
        composite_score = (
            weights["temporal"] * temporal_score
            + weights["dependency"] * dependency_score
            + weights["direction"] * direction_score
            + weights["severity"] * avg_sev
        )

        if composite_score < self.config.min_correlation_score:
            return None

        # Cluster overall severity
        has_critical = any(a.severity == SeverityLevel.CRITICAL for a in cluster)
        has_high = any(a.severity in (SeverityLevel.HIGH, SeverityLevel.ERROR) for a in cluster)
        cluster_sev = (
            SeverityLevel.CRITICAL
            if (has_critical or (has_high and len(distinct_metrics) >= 3))
            else (SeverityLevel.HIGH if has_high else SeverityLevel.MEDIUM)
        )

        candidate_id = uuid.uuid5(company_id, f"incident-cand-{start_t.isoformat()}-{len(cluster)}")
        metric_list_str = ", ".join(distinct_metrics[:4])
        if len(distinct_metrics) > 4:
            metric_list_str += f" (+{len(distinct_metrics) - 4} more)"

        title = f"Correlated Operational Incident across {metric_list_str}"
        summary = (
            f"Detected {len(cluster)} correlated anomalies across {len(distinct_metrics)} metrics "
            f"({metric_list_str}) within a {spread_mins:.0f}-minute temporal window. "
            f"Strong operational dependency alignment (score: {composite_score:.2f})."
        )

        return IncidentCandidate(
            candidate_id=candidate_id,
            company_id=company_id,
            title=title,
            preliminary_summary=summary,
            severity=cluster_sev,
            correlation_score=composite_score,
            first_detected_at=start_t,
            last_detected_at=end_t,
            affected_metrics=distinct_metrics,
            anomaly_ids=[a.id for a in cluster],
        )

    def _compute_dependency_score(self, metrics: list[str]) -> float:
        """Calculates graph connectivity ratio between metrics in the cluster."""
        graph = self.config.dependency_graph
        pairs_checked = 0
        connected_pairs = 0

        for i, m1 in enumerate(metrics):
            for m2 in metrics[i + 1 :]:
                pairs_checked += 1
                # Check direct or 1-hop path
                is_direct = (m2 in graph.get(m1, [])) or (m1 in graph.get(m2, []))
                if is_direct:
                    connected_pairs += 1.0
                else:
                    # 1-hop check
                    m1_neighbors = set(graph.get(m1, []))
                    m2_neighbors = set(graph.get(m2, []))
                    if m1_neighbors & set(graph.keys()) or m2_neighbors & set(graph.keys()):
                        connected_pairs += 0.5

        if pairs_checked == 0:
            return 0.5
        return min(1.0, max(0.25, connected_pairs / pairs_checked))

    def _compute_directional_score(self, cluster: list[Anomaly]) -> float:
        """Checks if deviations match expected operational symptom directions."""
        aligned_count = 0
        for a in cluster:
            metric_cfg = self.config.get_metric_config(a.metric_name)
            # Higher is worse and deviation > 0, or Lower is worse and deviation < 0
            if (metric_cfg.is_higher_worse and a.deviation > 0) or (
                not metric_cfg.is_higher_worse and a.deviation < 0
            ):
                aligned_count += 1
        return max(0.2, aligned_count / max(1, len(cluster)))
