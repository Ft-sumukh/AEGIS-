"""Unit tests for anti-hallucination evidence citation validation."""

from app.agents.investigator import AIInvestigator
from app.agents.schemas import Fact, HypothesisEvaluation, StructuredInvestigationOutput
from app.models.enums import HypothesisStatus


def test_valid_evidence_citations_accepted():
    investigator = AIInvestigator()
    known_evidence = {"ev-100", "dep-v2.1", "anom-9988"}

    output = StructuredInvestigationOutput(
        summary="Test summary",
        root_cause="Test cause",
        confidence=0.8,
        uncertainty=0.2,
        facts=[Fact(statement="Observed event", evidence_reference="ev-100")],
        hypotheses=[
            HypothesisEvaluation(
                title="Test Hypothesis",
                description="Test description",
                status=HypothesisStatus.SUPPORTED,
                confidence=0.8,
                supporting_evidence_ids=["dep-v2.1"],
            )
        ],
        evidence_citations=["ev-100", "dep-v2.1"],
    )

    investigator._validate_evidence_citations(output, known_evidence)
    # Valid citations should not produce constraint errors
    assert len(output.constraints_encountered) == 0


def test_hallucinated_evidence_citations_flagged():
    investigator = AIInvestigator()
    known_evidence = {"ev-100", "dep-v2.1"}

    # Cited an invented deployment that does not exist in known_evidence
    hallucinated_id = "DEPLOYMENT-HALLUCINATED-99999"
    output = StructuredInvestigationOutput(
        summary="Test summary",
        root_cause="Test cause",
        confidence=0.8,
        uncertainty=0.2,
        facts=[Fact(statement="Observed event", evidence_reference=hallucinated_id)],
        hypotheses=[
            HypothesisEvaluation(
                title="Test Hypothesis",
                description="Test description",
                status=HypothesisStatus.SUPPORTED,
                confidence=0.8,
                supporting_evidence_ids=[hallucinated_id],
            )
        ],
        evidence_citations=[hallucinated_id],
    )

    investigator._validate_evidence_citations(output, known_evidence)
    # The hallucinated citation must be detected and flagged
    assert len(output.constraints_encountered) > 0
    assert "Unverified evidence citations" in output.constraints_encountered[0]
