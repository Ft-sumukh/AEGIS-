"""Pydantic schemas for AI investigator structured outputs and evidence models."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import HypothesisStatus, SeverityLevel, TicketPriority


class Fact(BaseModel):
    """Empirically verified operational observation."""

    statement: str = Field(description="Directly observed factual event or metric value")
    evidence_reference: str = Field(description="Identifier or citation of the source record")
    timestamp: str | None = Field(default=None, description="ISO-8601 timestamp of observation")


class Inference(BaseModel):
    """Logical deduction connecting multiple observed facts."""

    statement: str = Field(description="Inference drawn from correlated facts")
    supporting_facts: list[str] = Field(
        default_factory=list, description="Statements of supporting facts"
    )


class HypothesisEvaluation(BaseModel):
    """Candidate root-cause hypothesis evaluated with evidence."""

    title: str = Field(description="Hypothesis title (e.g. Deployment Configuration Regression)")
    description: str = Field(description="Technical rationale and mechanism")
    status: HypothesisStatus = Field(
        default=HypothesisStatus.PROPOSED,
        description="PROPOSED, TESTING, SUPPORTED, REJECTED, INCONCLUSIVE",
    )
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="Confidence score [0.0, 1.0]"
    )
    supporting_evidence_ids: list[str] = Field(
        default_factory=list, description="List of validated evidence citations"
    )
    rejection_reason: str | None = Field(
        default=None, description="Explanation if status is REJECTED"
    )


class RecommendationPlan(BaseModel):
    """Corrective operational mitigation proposed by the investigator."""

    title: str = Field(description="Concise recommendation title")
    description: str = Field(description="Step-by-step mitigation or remediation procedure")
    priority: TicketPriority = Field(default=TicketPriority.HIGH)
    risk_level: SeverityLevel = Field(default=SeverityLevel.MEDIUM)
    expected_impact: str = Field(description="Projected operational outcome")


class Correlation(BaseModel):
    """Observed temporal or structural correlation across distinct operational domains."""

    statement: str = Field(description="Non-causal correlation statement linking events across sources")
    evidence_references: list[str] = Field(
        default_factory=list, description="Citations to correlated operational items (traces, deployments, metrics)"
    )
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Correlation confidence [0.0, 1.0]")


class StructuredInvestigationOutput(BaseModel):
    """Rigidly validated structured findings output from the AI Investigator."""

    summary: str = Field(description="Executive diagnosis summary")
    root_cause: str = Field(description="Identified or leading root cause hypothesis")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence level [0.0, 1.0]")
    uncertainty: float = Field(ge=0.0, le=1.0, description="Uncertainty margin [0.0, 1.0]")
    facts: list[Fact] = Field(default_factory=list, description="Observed operational facts")
    correlations: list[Correlation] = Field(
        default_factory=list, description="Observed non-causal multi-source correlations"
    )
    inferences: list[Inference] = Field(default_factory=list, description="Logical deductions")
    hypotheses: list[HypothesisEvaluation] = Field(
        default_factory=list, description="Evaluated candidate hypotheses"
    )
    recommendations: list[RecommendationPlan] = Field(
        default_factory=list, description="Actionable remediation proposals"
    )
    evidence_citations: list[str] = Field(
        default_factory=list, description="All evidence reference identifiers cited in findings"
    )
    uncertainty_notes: list[str] = Field(
        default_factory=list, description="Explicit data completeness, trace coverage, or sampling caveats"
    )
    constraints_encountered: list[str] = Field(
        default_factory=list,
        description="Any budget, time window, or data minimization constraints encountered",
    )

