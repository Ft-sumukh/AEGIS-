"""Integration tests for the Operations Intelligence Engine against synthetic enterprise telemetry."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.analytics.engine import OperationsIntelligenceEngine
from app.analytics.evaluation import BenchmarkEvaluator
from app.generator.config import GeneratorConfig
from app.generator.synthesizer import EnterpriseDataSynthesizer
from app.models.anomaly import Anomaly
from app.models.company import Company
from app.models.enums import CompanyStatus, SeverityLevel
from app.models.metrics import OperationalMetric


@pytest.fixture(scope="module")
def synthetic_engine_data():
    """Generates synthetic dataset for the 65-day enterprise simulation."""
    config = GeneratorConfig(
        days=65,
        customer_count=50,
        seed=42,
        start_date=datetime(2026, 6, 1, 0, 0, 0, tzinfo=UTC),
    )
    syn = EnterpriseDataSynthesizer(config)
    return syn.synthesize()


@pytest.fixture(scope="module")
def loaded_analytics_db(test_engine, synthetic_engine_data):
    """Loads synthetic metrics once and executes initial analysis run."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    raw_company = synthetic_engine_data.company
    company_id = uuid.UUID(raw_company["id"])

    # Create company record
    company = Company(
        id=company_id,
        name=raw_company["name"],
        slug=raw_company["slug"],
        industry=raw_company["industry"],
        status=CompanyStatus.ACTIVE,
        created_at=datetime.fromisoformat(raw_company["created_at"]),
    )
    session.add(company)
    session.flush()

    # Bulk insert operational metrics
    metrics_to_insert = [
        OperationalMetric(
            id=uuid.UUID(m["id"]),
            company_id=company_id,
            metric_name=m["metric_name"],
            timestamp=datetime.fromisoformat(m["timestamp"]),
            value=float(m["value"]),
            unit=m["unit"],
            source=m["source"],
            dimension_data=m.get("dimension_data", {}),
        )
        for m in synthetic_engine_data.metrics
    ]

    session.add_all(metrics_to_insert)
    session.commit()

    engine = OperationsIntelligenceEngine()
    record = engine.run_analysis(db=session, company_id=company_id)

    yield session, company_id, synthetic_engine_data, record, engine

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


def test_full_analytics_run_execution(loaded_analytics_db) -> None:
    """Executes the OperationsIntelligenceEngine pipeline and verifies run record audit."""
    _, company_id, _, record, _ = loaded_analytics_db

    assert record.status == "COMPLETED"
    assert record.company_id == company_id
    assert record.records_analyzed > 1000
    assert record.anomalies_detected > 0
    assert record.incident_candidates_generated >= 1
    assert "checkout_failure_rate" in record.metrics_analyzed
    assert "api_error_rate" in record.metrics_analyzed
    assert "revenue" in record.metrics_analyzed


def test_day60_checkout_incident_detection_and_correlation(loaded_analytics_db) -> None:
    """Verifies that the Day 60 checkout incident is detected across all affected metrics and correlated."""
    db, company_id, _, _, engine = loaded_analytics_db

    # Verify anomalies persisted in database
    anomalies = list(db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all())
    assert len(anomalies) > 0

    target_day = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=60)
    day60_anomalies = [
        a
        for a in anomalies
        if a.detected_at.date() == target_day.date() and 9 <= a.detected_at.hour <= 18
    ]

    flagged_metrics = {a.metric_name for a in day60_anomalies}
    assert "checkout_failure_rate" in flagged_metrics
    assert "api_error_rate" in flagged_metrics
    assert "api_latency" in flagged_metrics
    assert "revenue" in flagged_metrics

    # Verify incident candidate creation
    candidates = engine.get_incident_candidates(company_id=company_id)
    assert len(candidates) >= 1

    # Find the candidate matching the Day 60 incident window
    day60_candidates = [
        c
        for c in candidates
        if c.first_detected_at.date() == target_day.date()
        and "checkout_failure_rate" in c.affected_metrics
        and "api_error_rate" in c.affected_metrics
    ]
    assert len(day60_candidates) >= 1
    day60_candidate = max(day60_candidates, key=lambda c: len(c.affected_metrics))
    assert day60_candidate is not None
    assert day60_candidate.severity in (SeverityLevel.HIGH, SeverityLevel.CRITICAL)

    assert day60_candidate.correlation_score >= 0.55
    assert len(day60_candidate.affected_metrics) >= 2
    assert (
        "checkout_failure_rate" in day60_candidate.affected_metrics
        or "api_error_rate" in day60_candidate.affected_metrics
    )

    # Verify preliminary business blast radius
    assert day60_candidate.impact is not None
    assert day60_candidate.impact.is_preliminary is True
    assert day60_candidate.impact.estimated_revenue_impact >= 0


def test_benign_events_false_positive_resistance(loaded_analytics_db) -> None:
    """Verifies that benign flash sale (Day 22) does not create spurious critical checkout failures."""
    db, company_id, _, _, _ = loaded_analytics_db
    mkt_day = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=22)

    anomalies = list(db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all())

    # Day 22 daytime anomalies on checkout_failure_rate or api_error_rate should NOT be CRITICAL
    mkt_critical_anomalies = [
        a
        for a in anomalies
        if a.detected_at.date() == mkt_day.date()
        and a.metric_name in ("checkout_failure_rate", "api_error_rate")
        and a.severity == SeverityLevel.CRITICAL
    ]
    assert len(mkt_critical_anomalies) == 0


def test_benchmark_evaluator_quality(loaded_analytics_db) -> None:
    """Evaluates precision, recall, and F1 score against ground truth incident window."""
    db, company_id, dataset, _, _ = loaded_analytics_db
    anomalies = list(db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all())

    incident_start = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=60, hours=9)
    incident_end = datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=60, hours=18)
    affected_metrics = {"api_error_rate", "checkout_failure_rate", "api_latency", "revenue"}

    report = BenchmarkEvaluator.evaluate(
        detected_anomalies=anomalies,
        total_observations=len(dataset.metrics),
        incident_start=incident_start,
        incident_end=incident_end,
        affected_metrics=affected_metrics,
    )

    assert report.true_positives > 0
    assert report.recall >= 0.70
    assert report.precision >= 0.70
    assert report.f1_score >= 0.70


def test_analytics_run_idempotency(loaded_analytics_db) -> None:
    """Subsequent runs on the same dataset must be idempotent without duplicating anomalies."""
    db, company_id, _, _, engine = loaded_analytics_db

    count_before = len(
        list(db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all())
    )
    assert count_before > 0

    # Run analysis again
    record_second = engine.run_analysis(db=db, company_id=company_id)
    assert record_second.status == "COMPLETED"

    count_after = len(
        list(db.scalars(select(Anomaly).where(Anomaly.company_id == company_id)).all())
    )

    # Exactly identical number of anomalies (zero duplicate insertions)
    assert count_after == count_before
