"""Central Operations Intelligence Engine orchestrating detection, scoring, correlation, and impact."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.baseline import BaselineEngine
from app.analytics.config import AnalyticsConfig
from app.analytics.correlation import MultiMetricCorrelator
from app.analytics.detectors import (
    BaseDetector,
    PercentageChangeDetector,
    RollingBaselineDetector,
    SeasonalDetector,
    ThresholdDetector,
    TrendDetector,
    ZScoreDetector,
)
from app.analytics.impact import BusinessImpactEngine
from app.analytics.models import (
    AnalysisRunRecord,
    IncidentCandidate,
    MetricPoint,
    MetricSeries,
    RawAnomaly,
)
from app.analytics.scoring import AnomalyScorer
from app.core.logging import get_logger
from app.models.anomaly import Anomaly
from app.models.enums import AnomalyStatus
from app.models.metrics import OperationalMetric

logger = get_logger("aegis.analytics.engine")


class OperationsIntelligenceEngine:
    """End-to-end deterministic intelligence engine for operational telemetry."""

    # In-memory registry for executed runs and active incident candidates
    _run_history: list[AnalysisRunRecord] = []
    _incident_candidates: list[IncidentCandidate] = []

    def __init__(self, config: AnalyticsConfig | None = None) -> None:
        self.config = config or AnalyticsConfig()
        self.baseline_engine = BaselineEngine(min_samples=self.config.minimum_baseline_samples)
        self.scorer = AnomalyScorer(self.config)
        self.correlator = MultiMetricCorrelator(self.config)
        self.impact_engine = BusinessImpactEngine()

        # Modular detectors suite
        self.detectors: list[BaseDetector] = [
            ThresholdDetector(),
            PercentageChangeDetector(),
            ZScoreDetector(),
            RollingBaselineDetector(),
            SeasonalDetector(),
            TrendDetector(),
        ]

    def run_analysis(
        self,
        db: Session,
        company_id: uuid.UUID,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        metric_filter: list[str] | None = None,
    ) -> AnalysisRunRecord:
        """Executes full operational intelligence pipeline on database telemetry."""
        run_id = uuid.uuid4()
        started_at = datetime.now(UTC)

        run_record = AnalysisRunRecord(
            run_id=run_id,
            company_id=company_id,
            status="RUNNING",
            started_at=started_at,
        )
        self._run_history.append(run_record)

        logger.info(
            f"Starting analytics run {run_id} for company {company_id} "
            f"(window: {start_time} to {end_time})..."
        )

        try:
            # 1. Load telemetry metrics
            series_map = self._load_metric_series(
                db=db,
                company_id=company_id,
                start_time=start_time,
                end_time=end_time,
                metric_filter=metric_filter,
            )

            total_records = sum(len(s.points) for s in series_map.values())
            run_record.records_analyzed = total_records
            run_record.metrics_analyzed = sorted(series_map.keys())

            if not series_map:
                logger.warning(f"No metric data found for company {company_id}")
                run_record.status = "COMPLETED"
                run_record.completed_at = datetime.now(UTC)
                return run_record

            # 2. Run all detectors across metric series
            raw_anomalies: list[RawAnomaly] = []
            for m_name, series in series_map.items():
                for detector in self.detectors:
                    try:
                        detected = detector.detect(series, self.baseline_engine, self.config)
                        raw_anomalies.extend(detected)
                    except Exception as exc:
                        logger.error(
                            f"Detector {detector.__class__.__name__} failed on {m_name}: {exc}"
                        )
                        run_record.errors.append(
                            f"{detector.__class__.__name__} on {m_name}: {exc}"
                        )

            # 3. Score, deduplicate, and persist anomalies
            persisted_anomalies = self._persist_anomalies(db, raw_anomalies, company_id)
            run_record.anomalies_detected = len(persisted_anomalies)

            # 4. Multi-metric correlation & incident candidate generation
            candidates = self.correlator.correlate(persisted_anomalies, company_id)

            # 5. Estimate business impact for each incident candidate
            for cand in candidates:
                # Find anomalies linked to this candidate
                linked_anomalies = [a for a in persisted_anomalies if a.id in cand.anomaly_ids]
                cand.impact = self.impact_engine.estimate_impact(linked_anomalies)

            # Register candidates
            self._incident_candidates.extend(candidates)
            run_record.incident_candidates_generated = len(candidates)
            run_record.status = "COMPLETED"
            run_record.completed_at = datetime.now(UTC)

            logger.info(
                f"Analytics run {run_id} completed: {run_record.anomalies_detected} anomalies, "
                f"{len(candidates)} incident candidates from {total_records} observations."
            )
            return run_record

        except Exception as exc:
            logger.exception(f"Analytics run {run_id} failed: {exc}")
            run_record.status = "FAILED"
            run_record.completed_at = datetime.now(UTC)
            run_record.errors.append(str(exc))
            return run_record

    def _load_metric_series(
        self,
        db: Session,
        company_id: uuid.UUID,
        start_time: datetime | None,
        end_time: datetime | None,
        metric_filter: list[str] | None,
    ) -> dict[str, MetricSeries]:
        """Loads and sorts time-series metrics from PostgreSQL/SQLite."""
        stmt = select(OperationalMetric).where(OperationalMetric.company_id == company_id)
        if start_time:
            stmt = stmt.where(OperationalMetric.timestamp >= start_time)
        if end_time:
            stmt = stmt.where(OperationalMetric.timestamp <= end_time)
        if metric_filter:
            stmt = stmt.where(OperationalMetric.metric_name.in_(metric_filter))

        stmt = stmt.order_by(OperationalMetric.metric_name, OperationalMetric.timestamp.asc())
        records = db.scalars(stmt).all()

        series_map: dict[str, MetricSeries] = {}
        for r in records:
            if r.metric_name not in series_map:
                series_map[r.metric_name] = MetricSeries(
                    company_id=company_id,
                    metric_name=r.metric_name,
                    unit=r.unit,
                )
            series_map[r.metric_name].points.append(
                MetricPoint(
                    timestamp=r.timestamp,
                    value=r.value,
                    dimensions=r.dimension_data,
                    metric_id=r.id,
                )
            )

        return series_map

    def _persist_anomalies(
        self,
        db: Session,
        raw_anomalies: list[RawAnomaly],
        company_id: uuid.UUID,
    ) -> list[Anomaly]:
        """Scores, deduplicates against existing fingerprints, and saves anomalies to database."""
        if not raw_anomalies:
            return []

        # Query existing fingerprints for this company to guarantee idempotency
        existing_fingerprints = (
            set(
                db.scalars(
                    select(Anomaly.anomaly_metadata["fingerprint"].astext).where(
                        Anomaly.company_id == company_id
                    )
                ).all()
            )
            if db.bind.dialect.name == "postgresql"
            else set()
        )

        # For SQLite fallback, query existing tuples
        if db.bind.dialect.name != "postgresql":
            existing_anomalies = db.scalars(
                select(Anomaly).where(Anomaly.company_id == company_id)
            ).all()
            for ea in existing_anomalies:
                fp = ea.anomaly_metadata.get("fingerprint")
                if fp:
                    existing_fingerprints.add(fp)

        persisted: list[Anomaly] = []
        new_records: list[Anomaly] = []

        for raw in raw_anomalies:
            score = self.scorer.score(raw, company_id)
            if score.fingerprint in existing_fingerprints:
                continue

            anomaly_id = uuid.uuid5(company_id, score.fingerprint)
            anomaly = Anomaly(
                id=anomaly_id,
                company_id=company_id,
                metric_id=raw.metric_id,
                metric_name=raw.metric_name,
                detected_at=raw.timestamp,
                observed_value=raw.observed_value,
                expected_value=raw.expected_value,
                deviation=raw.deviation,
                detector_type=raw.detector_type,
                severity=score.severity,
                confidence=score.confidence,
                explanation=score.explanation,
                status=AnomalyStatus.NEW,
                anomaly_metadata=score.metadata,
                created_at=datetime.now(UTC),
            )
            new_records.append(anomaly)
            persisted.append(anomaly)
            existing_fingerprints.add(score.fingerprint)

        if new_records:
            db.add_all(new_records)
            db.commit()

        # Also retrieve existing anomalies in the window if repeat query to populate correlation
        all_window_anomalies = list(
            db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all()
        )
        return all_window_anomalies if all_window_anomalies else persisted

    @classmethod
    def get_run_history(cls) -> list[AnalysisRunRecord]:
        """Returns in-memory registry of executed runs."""
        return cls._run_history

    @classmethod
    def get_incident_candidates(
        cls, company_id: uuid.UUID | None = None
    ) -> list[IncidentCandidate]:
        """Returns registered incident candidates filtered optionally by company."""
        if company_id:
            return [c for c in cls._incident_candidates if c.company_id == company_id]
        return cls._incident_candidates
