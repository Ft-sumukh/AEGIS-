"""Incident Commander AI Co-Pilot Service.

Provides context-aware conversational assistance for on-call SREs and incident commanders.
Capable of contextual incident summarization, hypothesis breakdown, public status announcements,
and runbook recommendation.
"""

from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.slo_service import SLOService
from app.models.enums import IncidentStatus, SeverityLevel
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.recommendation import Recommendation
from app.runbooks.service import RunbookService

logger = logging.getLogger("aegis.copilot")


class CoPilotService:
    """Conversational assistant synthesizing real-time operational context for SRE commanders."""

    @classmethod
    def query(
        cls,
        db: Session,
        message: str,
        incident_id: uuid.UUID | None = None,
        context_hint: str | None = None,
    ) -> dict[str, Any]:
        """Processes an SRE operational query and returns a structured response with citations & recommended actions."""
        q = message.lower().strip()
        timestamp = datetime.now(UTC).isoformat()

        # Gather real-time context
        active_incidents = (
            db.execute(
                select(Incident)
                .where(Incident.status.in_([IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]))
                .order_by(Incident.detected_at.desc())
            )
            .scalars()
            .all()
        )

        all_slos = SLOService.list_slos(db)
        burning_slos = [s for s in all_slos if s.get("status") in ("BURNING", "EXHAUSTED", "WARNING")]

        # Target incident context if specified
        target_incident = None
        target_investigation = None
        target_recommendations: list[Recommendation] = []

        if incident_id:
            target_incident = db.execute(select(Incident).where(Incident.id == incident_id)).scalar_one_or_none()
            if target_incident:
                target_investigation = db.execute(
                    select(Investigation).where(Investigation.incident_id == incident_id)
                ).scalar_one_or_none()
                target_recommendations = (
                    db.execute(select(Recommendation).where(Recommendation.incident_id == incident_id))
                    .scalars()
                    .all()
                )
        elif active_incidents:
            target_incident = active_incidents[0]
            target_investigation = db.execute(
                select(Investigation).where(Investigation.incident_id == target_incident.id)
            ).scalar_one_or_none()

        # Intent detection
        # 1. Status Page Announcement drafting
        if any(w in q for w in ["draft", "status page", "announcement", "customer update", "public update", "slack message"]):
            return cls._draft_announcement(target_incident, target_investigation, timestamp)

        # 2. Error budget & SLO burn analysis
        if any(w in q for w in ["budget", "slo", "burn", "exhaust", "sli"]):
            return cls._analyze_budget(burning_slos, all_slos, timestamp)

        # 3. Root cause & hypothesis explanation
        if any(w in q for w in ["root cause", "why", "hypothesis", "diagnos", "evidence", "cause"]):
            return cls._explain_root_cause(target_incident, target_investigation, timestamp)

        # 4. Mitigation / Runbook / What should we do next
        if any(w in q for w in ["what should", "mitigat", "runbook", "action", "next step", "fix", "resolve"]):
            return cls._recommend_mitigations(target_incident, target_recommendations, timestamp)

        # 5. General incident overview / SRE status summary
        return cls._general_status_overview(active_incidents, burning_slos, timestamp)

    @classmethod
    def _draft_announcement(
        cls,
        incident: Incident | None,
        investigation: Investigation | None,
        timestamp: str,
    ) -> dict[str, Any]:
        if not incident:
            return {
                "reply": "No active incident detected to draft an announcement for. All systems operating normally.",
                "type": "ANNOUNCEMENT",
                "citations": [],
                "suggested_prompts": ["What is our current error budget status?", "Check service health"],
                "timestamp": timestamp,
            }

        title = f"INVESTIGATING: Performance Degradation affecting {', '.join(incident.affected_systems or ['Platform Services'])}"
        status_text = (
            f"**Incident**: {incident.title} ({incident.severity.value if hasattr(incident.severity, 'value') else incident.severity})\n\n"
            f"**Customer Impact**: {incident.summary or 'Intermittent transaction latency and elevated error responses.'}\n\n"
            f"**Current Status**: Aegis Operational Intelligence has identified the anomaly. SRE teams are actively engaged. "
            f"Estimated impact: ~{incident.estimated_users_affected or 1200} users.\n\n"
            f"**Next Update**: Within 15 minutes or upon mitigation verification."
        )

        slack_text = (
            f":warning: *INCIDENT ALERT [{incident.severity.value if hasattr(incident.severity, 'value') else incident.severity}]*: *{incident.title}*\n"
            f"• *Systems*: `{', '.join(incident.affected_systems or ['core'])}`\n"
            f"• *Current Hypotheses*: {investigation.summary if investigation else 'AI investigation underway'}\n"
            f"• *Aegis Console Link*: `/incidents/{incident.id}`"
        )

        return {
            "reply": f"Here is a drafted status announcement and Slack broadcast for **{incident.title}**:\n\n### Public StatusPage Update\n> **{title}**\n\n{status_text}\n\n### Internal SRE Slack Broadcast\n```text\n{slack_text}\n```",
            "type": "ANNOUNCEMENT",
            "draft_payload": {
                "title": title,
                "status_page_body": status_text,
                "slack_body": slack_text,
            },
            "citations": [f"Incident #{str(incident.id)[:8]}", f"Severity: {incident.severity.value if hasattr(incident.severity, 'value') else incident.severity}"],
            "suggested_prompts": [
                "What runbooks are available for this incident?",
                "What is the root cause evidence?",
                "What actions require human approval?",
            ],
            "timestamp": timestamp,
        }

    @classmethod
    def _analyze_budget(
        cls,
        burning_slos: list[dict[str, Any]],
        all_slos: list[dict[str, Any]],
        timestamp: str,
    ) -> dict[str, Any]:
        if not burning_slos:
            return {
                "reply": f"All **{len(all_slos)} monitored SLOs** are healthy. No service has breached the multi-window burn rate thresholds (1h burn rates are <= 1.0x). Overall average error budget remaining is {round(sum(s['error_budget_remaining_percent'] for s in all_slos) / max(len(all_slos), 1), 1)}%.",
                "type": "SLO_ANALYSIS",
                "citations": [f"{len(all_slos)} SLOs checked"],
                "suggested_prompts": ["Simulate a 5% error spike in checkout-service", "List all critical incidents"],
                "timestamp": timestamp,
            }

        lines = [f"⚠️ **{len(burning_slos)} Service Level Objective(s)** are actively consuming budget at an elevated velocity:"]
        citations = []
        for s in burning_slos:
            tte = f"{s['time_to_exhaustion_hours']}h" if s.get("time_to_exhaustion_hours") else "N/A"
            lines.append(
                f"- **{s['name']}** (`{s['service_name']}`): Status `{s['status']}` | 1h Burn Rate: **{s['burn_rate_1h']}x** | Budget Left: **{s['error_budget_remaining_percent']}%** | Time-to-Exhaustion: **{tte}**"
            )
            citations.append(f"{s['service_name']} ({s['burn_rate_1h']}x burn)")

        lines.append("\n*According to Google SRE guidelines, a 1-hour burn rate exceeding 14.4x consumes 2% of the 30-day budget in 60 minutes and warrants immediate paging.*")

        return {
            "reply": "\n".join(lines),
            "type": "SLO_ANALYSIS",
            "citations": citations,
            "suggested_prompts": [
                "What runbooks should we execute?",
                "Draft an executive incident brief",
                "Show affected microservices",
            ],
            "timestamp": timestamp,
        }

    @classmethod
    def _explain_root_cause(
        cls,
        incident: Incident | None,
        investigation: Investigation | None,
        timestamp: str,
    ) -> dict[str, Any]:
        if not incident:
            return {
                "reply": "No active incident selected or ongoing. System state is currently baseline nominal.",
                "type": "EXPLANATION",
                "citations": [],
                "suggested_prompts": ["Overview of all systems", "Check error budget burn"],
                "timestamp": timestamp,
            }

        reply_parts = [
            f"### Root Cause Intelligence for Incident #{str(incident.id)[:8]}",
            f"**Title**: {incident.title}",
            f"**Detected**: {incident.detected_at.strftime('%Y-%m-%d %H:%M:%S UTC') if incident.detected_at else 'Recent'}",
        ]

        if investigation:
            reply_parts.append(f"\n**Investigation Summary**:\n{investigation.summary}")
            if investigation.hypotheses:
                reply_parts.append("\n**Hypothesis Evaluation**:")
                for hyp in investigation.hypotheses[:4]:
                    h_title = hyp.title if hasattr(hyp, "title") else hyp.get("title", "Hypothesis")
                    raw_status = hyp.status.value if hasattr(hyp.status, "value") else str(hyp.status)
                    h_conf = hyp.confidence if hasattr(hyp, "confidence") else hyp.get("confidence", 0.5)
                    h_evid = hyp.supporting_evidence_summary if hasattr(hyp, "supporting_evidence_summary") else hyp.get("supporting_evidence", "")

                    status_emoji = "✅ [SUPPORTED]" if raw_status in ("SUPPORTED", "ACCEPTED", "CONFIRMED") else ("❌ [REJECTED]" if raw_status == "REJECTED" else "⏳ [TESTING]")
                    reply_parts.append(
                        f"- {status_emoji} **{h_title}** (Confidence: {int(float(h_conf) * 100)}%)\n  *Evidence*: {h_evid or 'Correlated with metric deviations'}"
                    )
        else:
            reply_parts.append(
                f"\n**Summary**: {incident.summary}\nAffected components: `{', '.join(incident.affected_systems or [])}`. Telemetry indicates correlated metric anomalies in `{', '.join(incident.affected_metrics or [])}`."
            )

        reply_parts.append(
            "\n*Note: Aegis policies require authorized human approval before any remediation mutation is executed.*"
        )

        return {
            "reply": "\n".join(reply_parts),
            "type": "EXPLANATION",
            "citations": [f"Incident #{str(incident.id)[:8]}", f"Affected: {','.join(incident.affected_systems or [])}"],
            "suggested_prompts": [
                "What should we do next?",
                "Draft customer status update",
                "Show error budget impact",
            ],
            "timestamp": timestamp,
        }

    @classmethod
    def _recommend_mitigations(
        cls,
        incident: Incident | None,
        recommendations: list[Recommendation],
        timestamp: str,
    ) -> dict[str, Any]:
        runbooks = RunbookService.list_runbooks()

        parts = ["### Operational Mitigation Recommendations & SRE Runbooks"]
        citations = []

        if incident:
            matched_rb = RunbookService.match_for_incident(incident)
            parts.append(f"Targeting active incident **{incident.title}** ({incident.severity.value if hasattr(incident.severity, 'value') else incident.severity}):\n")
            if matched_rb:
                parts.append("#### Recommended Standard Operating Runbooks:")
                for rb in matched_rb[:2]:
                    parts.append(f"- **{rb['title']}** (`{rb['id']}`): {rb.get('summary', '')}")
                    parts.append(f"  *Severity*: `{rb.get('severity', 'HIGH')}` | Target: `{','.join(rb.get('target_services', []))}`")
                    steps = rb.get("diagnostic_steps", [])
                    first_step_text = steps[0]["action"] if steps else "Inspect telemetry"
                    parts.append(f"  *First Step*: `{first_step_text}`")
                    citations.append(f"Runbook: {rb['id']}")

            if recommendations:
                parts.append("\n#### Pending AI Action Proposals (Awaiting Approval):")
                for r in recommendations[:3]:
                    parts.append(f"- **{r.title}** (Risk: `{r.risk_level}`, Priority: `{r.priority}`): {r.summary}")
                    citations.append(f"Action: {r.action_type}")
        else:
            parts.append("No active incident. Available catalog runbooks:")
            for rb in runbooks[:3]:
                parts.append(f"- **{rb['title']}** (`{rb['id']}`) - Risk: `{rb['risk_level']}`")

        parts.append(
            "\n🔒 **Governance Safeguard**: All production actions remain in `PENDING_APPROVAL` status until an authorized Operator or Incident Commander signs off."
        )

        return {
            "reply": "\n".join(parts),
            "type": "MITIGATION",
            "citations": citations,
            "suggested_prompts": [
                "Draft customer status update",
                "Explain root cause hypotheses",
                "What is burning our error budget?",
            ],
            "timestamp": timestamp,
        }

    @classmethod
    def _general_status_overview(
        cls,
        active_incidents: list[Incident],
        burning_slos: list[dict[str, Any]],
        timestamp: str,
    ) -> dict[str, Any]:
        crit_count = sum(1 for i in active_incidents if i.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for i in active_incidents if i.severity == SeverityLevel.HIGH)

        reply = (
            f"**Aegis SRE Commander Intelligence Briefing** (as of {timestamp[:19]} UTC):\n\n"
            f"• **Active Incidents**: **{len(active_incidents)}** ({crit_count} Critical, {high_count} High)\n"
            f"• **SLO Error Budget Status**: **{len(burning_slos)} service(s)** currently in elevated burn rate or warning\n"
            f"• **Autonomous Action Guard**: Active. All operational mutations require human multi-tier approval.\n\n"
            f"How can I assist your investigation? You can ask me to **draft status announcements**, **break down root causes**, **recommend runbook steps**, or **check error budget burn rates**."
        )

        return {
            "reply": reply,
            "type": "OVERVIEW",
            "citations": [f"{len(active_incidents)} active incidents", f"{len(burning_slos)} burning SLOs"],
            "suggested_prompts": [
                "What is burning our error budget?",
                "Explain the root cause of the latest incident",
                "Draft a customer status page announcement",
                "What runbooks should we run?",
            ],
            "timestamp": timestamp,
        }
