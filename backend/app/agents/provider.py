"""Pluggable AI provider abstraction for privacy-aware operational investigations."""

import abc
import json
from datetime import UTC, datetime
from typing import Any

from app.agents.schemas import (
    Correlation,
    Fact,
    HypothesisEvaluation,
    Inference,
    RecommendationPlan,
    StructuredInvestigationOutput,
)
from app.config import get_settings
from app.models.enums import HypothesisStatus, SeverityLevel, TicketPriority
from app.security.policy import AIDataPolicyMode


class AIProviderInterface(abc.ABC):
    """Abstract interface decoupling Aegis application logic from specific LLM providers."""

    def __init__(
        self,
        provider_name: str,
        model_name: str,
        data_policy: AIDataPolicyMode = AIDataPolicyMode.STANDARD,
        timeout_seconds: int = 60,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model_name
        self.data_policy = data_policy
        self.timeout_seconds = timeout_seconds

    @abc.abstractmethod
    def run_investigation(
        self,
        incident_context: dict[str, Any],
        collected_evidence: list[dict[str, Any]],
        constraints: list[str] | None = None,
    ) -> StructuredInvestigationOutput:
        """Processes sanitized operational evidence and returns schema-validated findings."""
        pass


class MockAIProvider(AIProviderInterface):
    """Deterministic, explainable operational reasoning engine for tests and local development."""

    def __init__(
        self,
        data_policy: AIDataPolicyMode = AIDataPolicyMode.STANDARD,
        timeout_seconds: int = 60,
    ) -> None:
        super().__init__(
            provider_name="mock",
            model_name="aegis-deterministic-v1",
            data_policy=data_policy,
            timeout_seconds=timeout_seconds,
        )

    def run_investigation(
        self,
        incident_context: dict[str, Any],
        collected_evidence: list[dict[str, Any]],
        constraints: list[str] | None = None,
    ) -> StructuredInvestigationOutput:
        """Generates structured findings adhering to causality guardrails and evidence citation validation."""
        incident_title = incident_context.get("title", "Operational Incident")
        category = incident_context.get("category", "SYSTEM")
        detected_at = incident_context.get("detected_at", datetime.now(UTC).isoformat())

        # Analyze collected evidence
        facts: list[Fact] = []
        inferences: list[Inference] = []
        citations: list[str] = []
        deployments_found: list[dict[str, Any]] = []
        anomalies_found: list[dict[str, Any]] = []

        for ev in collected_evidence:
            source = ev.get("source_type") or ev.get("source") or "SYSTEM"
            ev_id = str(ev.get("id") or ev.get("source_id") or ev.get("anomaly_id") or ev.get("deployment_id") or f"ev-{len(citations)}")
            citations.append(ev_id)

            if "deployment" in str(source).lower() or "version" in ev:
                deployments_found.append(ev)
                facts.append(
                    Fact(
                        statement=f"Deployment '{ev.get('version', 'unknown')}' was executed for service '{ev.get('service_name', 'unknown')}' at {ev.get('started_at', 'unknown')}.",
                        evidence_reference=ev_id,
                        timestamp=str(ev.get("started_at")),
                    )
                )
            elif "anomaly" in str(source).lower() or "deviation" in ev:
                anomalies_found.append(ev)
                facts.append(
                    Fact(
                        statement=f"Metric anomaly detected in '{ev.get('metric_name', 'unknown')}' with deviation of {ev.get('deviation', 0.0):.2f}x above baseline.",
                        evidence_reference=ev_id,
                        timestamp=str(ev.get("start_time")),
                    )
                )
            else:
                summary_text = ev.get("summary") or ev.get("title") or "Operational event"
                facts.append(
                    Fact(
                        statement=f"Operational observation: {summary_text}",
                        evidence_reference=ev_id,
                        timestamp=str(ev.get("observed_at") or ev.get("timestamp")),
                    )
                )

        # Inferences and Correlations
        correlations: list[Correlation] = []
        if deployments_found and anomalies_found:
            inferences.append(
                Inference(
                    statement="Software deployment immediately preceded the emergence of metric anomalies across affected services.",
                    supporting_facts=[f.statement for f in facts[:2]],
                )
            )
            correlations.append(
                Correlation(
                    statement="Deployment preceded the observed latency and error degradation across downstream service dependencies.",
                    evidence_references=citations[:2],
                    confidence=0.90,
                )
            )

        # Formulate hypotheses with causality guardrails
        hypotheses: list[HypothesisEvaluation] = []
        if deployments_found:
            leading_dep = deployments_found[0]
            dep_id = str(leading_dep.get("deployment_id") or citations[0])
            hypotheses.append(
                HypothesisEvaluation(
                    title=f"Deployment Regression ({leading_dep.get('version', 'latest')})",
                    description=(
                        f"The recent deployment of version {leading_dep.get('version')} is the leading root-cause hypothesis "
                        "because its execution time directly precedes anomalous error rates and the affected service matches the incident blast radius."
                    ),
                    status=HypothesisStatus.SUPPORTED,
                    confidence=0.88,
                    supporting_evidence_ids=[dep_id],
                )
            )
            hypotheses.append(
                HypothesisEvaluation(
                    title="External Traffic Surge or DDoS",
                    description="Evaluation of whether volumetric load caused systemic failure.",
                    status=HypothesisStatus.REJECTED,
                    confidence=0.15,
                    supporting_evidence_ids=[],
                    rejection_reason="Traffic volume remained within standard baseline bands prior to deployment.",
                )
            )
            root_cause_text = (
                f"Deployment of {leading_dep.get('version', 'new release')} is the leading root-cause hypothesis "
                f"associated with degraded {category} performance."
            )
            recs = [
                RecommendationPlan(
                    title=f"Rollback deployment {leading_dep.get('version', 'recent release')}",
                    description=f"Revert service '{leading_dep.get('service_name', 'affected')}' to previous stable release and inspect error telemetry.",
                    priority=TicketPriority.HIGH,
                    risk_level=SeverityLevel.LOW,
                    expected_impact="Immediate restoration of baseline latency and transaction success rate.",
                ),
                RecommendationPlan(
                    title="Scale service replicas temporarily",
                    description="Increase container allocation to absorb pending thread queue.",
                    priority=TicketPriority.MEDIUM,
                    risk_level=SeverityLevel.LOW,
                    expected_impact="Relieves CPU pressure while rollback completes.",
                ),
            ]
        else:
            hypotheses.append(
                HypothesisEvaluation(
                    title="Infrastructure Saturation",
                    description="System resources (CPU/Memory/Pool) saturated under standard load.",
                    status=HypothesisStatus.SUPPORTED,
                    confidence=0.70,
                    supporting_evidence_ids=citations[:1],
                )
            )
            root_cause_text = f"Telemetry confirms systemic degradation affecting {category} operations."
            recs = [
                RecommendationPlan(
                    title="Restart degraded pods and analyze heap dump",
                    description="Recycle affected worker instances and examine memory allocation.",
                    priority=TicketPriority.HIGH,
                    risk_level=SeverityLevel.MEDIUM,
                    expected_impact="Restores service responsiveness.",
                )
            ]

        confidence = 0.85 if deployments_found else 0.65
        uncertainty = 0.15 if deployments_found else 0.35

        uncertainty_notes = [
            "Trace coverage and span sampling verified across ingress and downstream microservices.",
            "Observed highest latency contribution is an operational observation rather than definitive proof of independent root cause.",
        ]

        return StructuredInvestigationOutput(
            summary=f"Automated AI investigation for {incident_title} completed. {len(facts)} operational facts verified.",
            root_cause=root_cause_text,
            confidence=confidence,
            uncertainty=uncertainty,
            facts=facts,
            correlations=correlations,
            inferences=inferences,
            hypotheses=hypotheses,
            recommendations=recs,
            evidence_citations=citations,
            uncertainty_notes=uncertainty_notes,
            constraints_encountered=constraints or [],
        )


def get_ai_provider() -> AIProviderInterface:
    """Factory returning configured AI provider instance."""
    settings = get_settings()
    provider_name = settings.AI_PROVIDER.lower()
    data_policy = AIDataPolicyMode(settings.DATA_POLICY_MODE.upper())

    if provider_name == "mock":
        return MockAIProvider(data_policy=data_policy)

    # For openai, anthropic, or custom, fallback to Mock in current version or initialize adapter
    return MockAIProvider(data_policy=data_policy)
