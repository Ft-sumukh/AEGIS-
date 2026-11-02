"""AI Investigation and Operations intelligence agents module for Aegis."""

from app.agents.investigator import AIInvestigator, EvidenceReferenceValidationError
from app.agents.provider import AIProviderInterface, MockAIProvider, get_ai_provider
from app.agents.schemas import (
    Fact,
    HypothesisEvaluation,
    Inference,
    RecommendationPlan,
    StructuredInvestigationOutput,
)
from app.agents.tools import get_default_tool_registry
from app.agents.tools.registry import ALLOWED_TOOLS, FORBIDDEN_TOOLS, ToolRegistry, ToolSecurityError

__all__ = [
    "ALLOWED_TOOLS",
    "AIInvestigator",
    "AIProviderInterface",
    "EvidenceReferenceValidationError",
    "FORBIDDEN_TOOLS",
    "Fact",
    "HypothesisEvaluation",
    "Inference",
    "MockAIProvider",
    "RecommendationPlan",
    "StructuredInvestigationOutput",
    "ToolRegistry",
    "ToolSecurityError",
    "get_ai_provider",
    "get_default_tool_registry",
]
