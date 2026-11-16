"""Unit and integration test for Aegis End-to-End Benchmark Suite."""

import pytest
from sqlalchemy.orm import Session

from app.analytics.benchmark import AegisE2EBenchmarkRunner, E2EBenchmarkReport


def test_e2e_benchmark_runner_execution(db_session: Session):
    """Verify that the end-to-end benchmark harness executes all 5 stages and passes."""
    runner = AegisE2EBenchmarkRunner(db=db_session)
    report = runner.run_full_benchmark()

    assert isinstance(report, E2EBenchmarkReport)
    assert report.overall_status == "PASSED"
    assert len(report.stages) == 5

    # Stage 1: Anomaly Detection
    detection_stage = next(s for s in report.stages if s.stage_name == "ANOMALY_DETECTION")
    assert detection_stage.passed is True
    assert report.detection_recall >= 0.85
    assert report.detection_precision >= 0.80

    # Stage 2: Correlation & Incident Synthesis
    corr_stage = next(s for s in report.stages if s.stage_name == "CORRELATION_AND_INCIDENT_SYNTHESIS")
    assert corr_stage.passed is True
    assert corr_stage.metrics["raw_anomalies_consolidated"] > 0

    # Stage 3: AI Diagnostic Investigation
    investigation_stage = next(s for s in report.stages if s.stage_name == "AI_DIAGNOSTIC_INVESTIGATION")
    assert investigation_stage.passed is True
    assert investigation_stage.metrics["confidence"] >= 0.85

    # Stage 4: Human Approval & Cryptographic Gating
    gating_stage = next(s for s in report.stages if s.stage_name == "HUMAN_APPROVAL_AND_CRYPTO_GATING")
    assert gating_stage.passed is True
    assert report.human_gating_verified is True
    assert gating_stage.metrics["ai_approval_blocked"] is True
    assert gating_stage.metrics["tamper_detected"] is True

    # Stage 5: Execution & Verification
    exec_stage = next(s for s in report.stages if s.stage_name == "EXECUTION_AND_VERIFICATION_RECOVERY")
    assert exec_stage.passed is True
    assert report.remediation_recovery_rate == 1.0

    # Serialization
    report_dict = report.to_dict()
    assert report_dict["overall_status"] == "PASSED"
    assert "summary_kpis" in report_dict
    assert len(report_dict["stages"]) == 5
