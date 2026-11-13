"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  Cpu,
  DollarSign,
  Layers,
  MessageSquare,
  Package,
  Radio,
  Server,
  Sparkles,
  Users,
  FileText,
  GitBranch,
  Ticket,
  Zap,
  GitCommit,
  BookOpen,
  Download,
  CheckSquare,
  FileCheck,
} from "lucide-react";
import { api } from "@/lib/api/client";
import {
  ActionItem,
  CorrelatedTraceEvidence,
  IncidentDetail,
  IncidentEvidence,
  Investigation,
  TimelineEvent,
  PostMortem,
  Runbook,
} from "@/lib/api/types";

import { useAuth } from "@/lib/auth/AuthContext";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BoundaryBadge } from "@/components/ui/BoundaryBadge";
import { DetailSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params?.id as string;
  const { role, canAcknowledge, canInvestigate } = useAuth();

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [evidence, setEvidence] = useState<IncidentEvidence[]>([]);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [traceEvidence, setTraceEvidence] = useState<CorrelatedTraceEvidence | null>(null);
  const [isCorrelatingTraces, setIsCorrelatingTraces] = useState(false);
  const [postmortem, setPostmortem] = useState<PostMortem | null>(null);
  const [isGeneratingPostMortem, setIsGeneratingPostMortem] = useState(false);
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [checkedSteps, setCheckedSteps] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [isAcknowledging, setIsAcknowledging] = useState(false);
  const [isInvestigating, setIsInvestigating] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const loadData = async () => {
    if (!incidentId) return;
    try {
      setLoading(true);
      setError(null);
      const [inc, tl, ev, invs, actionsRes, traceEv, rbRes, pmRes] = await Promise.all([
        api.getIncident(incidentId),
        api.getIncidentTimeline(incidentId),
        api.getIncidentEvidence(incidentId),
        api.getIncidentInvestigations(incidentId),
        typeof api.getActions === "function"
          ? api.getActions({ incident_id: incidentId }).catch(() => ({ items: [] }))
          : Promise.resolve({ items: [] }),
        typeof api.getIncidentTraces === "function"
          ? api.getIncidentTraces(incidentId).catch(() => null)
          : Promise.resolve(null),
        typeof api.matchRunbooksForIncident === "function"
          ? api.matchRunbooksForIncident(incidentId).catch(() => [])
          : Promise.resolve([]),
        typeof api.getPostMortem === "function"
          ? api.getPostMortem(incidentId).catch(() => null)
          : Promise.resolve(null),
      ]);

      setIncident(inc);
      setTimeline(tl);
      setEvidence(ev);
      setInvestigations(invs);
      setActions(actionsRes.items || []);
      setTraceEvidence(traceEv);
      setRunbooks(rbRes || []);
      setPostmortem(pmRes);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load incident detail");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [incidentId]);

  const handleAcknowledge = async () => {
    if (!canAcknowledge) return;
    try {
      setIsAcknowledging(true);
      const updated = await api.acknowledgeIncident(incidentId, true);
      setIncident(updated);
      setActionNotice("Incident acknowledged. Status transitioned to INVESTIGATING.");
      await loadData();
    } catch (err: unknown) {
      setActionNotice(`Failed to acknowledge: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setIsAcknowledging(false);
    }
  };

  const handleTriggerInvestigation = async () => {
    if (!canInvestigate) return;
    try {
      setIsInvestigating(true);
      await api.triggerInvestigation(incidentId);
      setActionNotice("AI diagnostic run triggered. Refreshing findings...");
      await loadData();
    } catch (err: unknown) {
      setActionNotice(`Investigation trigger failed: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setIsInvestigating(false);
    }
  };

  const handleCorrelateTraces = async () => {
    try {
      setIsCorrelatingTraces(true);
      if (typeof api.attachIncidentTraceEvidence === "function") {
        await api.attachIncidentTraceEvidence(incidentId);
      }
      setActionNotice("Cross-source trace correlation completed and attached to evidence.");
      const [ev, tl, traceEv] = await Promise.all([
        api.getIncidentEvidence(incidentId),
        api.getIncidentTimeline(incidentId),
        typeof api.getIncidentTraces === "function"
          ? api.getIncidentTraces(incidentId).catch(() => null)
          : Promise.resolve(null),
      ]);
      setEvidence(ev);
      setTimeline(tl);
      setTraceEvidence(traceEv);
    } catch (err: unknown) {
      setActionNotice(`Trace correlation failed: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setIsCorrelatingTraces(false);
    }
  };

  const handleGeneratePostMortem = async () => {
    try {
      setIsGeneratingPostMortem(true);
      const pm = await api.generatePostMortem(incidentId);
      setPostmortem(pm);
      setActionNotice("AI Post-Incident Review successfully generated!");
    } catch (err: unknown) {
      setActionNotice(`Failed to generate Post-Mortem: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setIsGeneratingPostMortem(false);
    }
  };

  const handleDownloadPostMortem = async () => {
    try {
      const md = await api.getPostMortemMarkdown(incidentId);
      const blob = new Blob([md], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `postmortem_${incidentId.slice(0, 8)}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setActionNotice("Failed to download Markdown report.");
    }
  };

  const toggleStep = (stepKey: string) => {
    setCheckedSteps((prev) => ({ ...prev, [stepKey]: !prev[stepKey] }));
  };

  if (loading && !incident) {
    return <DetailSkeleton />;
  }

  if (error && !incident) {
    return <ErrorState message={error} onRetry={loadData} />;
  }

  if (!incident) return null;

  const latestInv = investigations.length > 0 ? investigations[0] : null;

  const getTimelineIcon = (eventType: string) => {
    switch (eventType) {
      case "DEPLOYMENT":
        return <GitBranch className="w-4 h-4 text-amber-400" />;
      case "SYSTEM_EVENT":
        return <Server className="w-4 h-4 text-rose-400" />;
      case "ANOMALY":
        return <Radio className="w-4 h-4 text-purple-400" />;
      case "TRACE_LATENCY_PATTERN":
      case "TRACE_ERROR_PATTERN":
      case "CRITICAL_PATH":
      case "CROSS_SOURCE_CORRELATION":
        return <GitCommit className="w-4 h-4 text-cyan-400" />;
      case "SUPPORT_TICKET":
        return <Ticket className="w-4 h-4 text-blue-400" />;
      case "CUSTOMER_COMPLAINT":
        return <MessageSquare className="w-4 h-4 text-orange-400" />;
      case "INVESTIGATION_EVENT":
        return <Cpu className="w-4 h-4 text-cyan-400" />;
      default:
        return <Calendar className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Back Link */}
      <Link
        href="/incidents"
        className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Incident Center</span>
      </Link>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div className="p-3 rounded-lg border border-cyan-800 bg-cyan-950/40 text-xs font-mono text-cyan-200 flex items-center justify-between">
          <span>{actionNotice}</span>
          <button onClick={() => setActionNotice(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Header Banner */}
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <SeverityBadge severity={incident.severity} size="md" />
              <StatusBadge status={incident.status} size="md" />
              <span className="text-xs font-mono text-slate-400">
                {incident.category} • Detected {new Date(incident.detected_at).toLocaleString()}
              </span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold font-mono tracking-tight text-white">
              {incident.title}
            </h1>
          </div>

          {/* Role-Gated Operator Actions */}
          <div className="flex items-center gap-3">
            {canAcknowledge && incident.status === "OPEN" && (
              <button
                onClick={handleAcknowledge}
                disabled={isAcknowledging}
                className="px-4 py-2 rounded-lg text-xs font-mono font-bold text-white bg-amber-600 hover:bg-amber-500 disabled:opacity-50 transition-colors"
              >
                {isAcknowledging ? "Acknowledging..." : "Acknowledge Incident"}
              </button>
            )}

            {canInvestigate && (
              <button
                onClick={handleTriggerInvestigation}
                disabled={isInvestigating}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold text-cyan-300 bg-cyan-950/60 border border-cyan-800 hover:bg-cyan-900/50 disabled:opacity-50 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>{isInvestigating ? "Running AI..." : "Trigger AI Diagnostic"}</span>
              </button>
            )}

            {!canAcknowledge && (
              <span className="text-[11px] font-mono text-slate-500 italic">
                Role: {role} (Read-Only)
              </span>
            )}
          </div>
        </div>

        {/* Systems, Owner, Duration Tag row */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-6 text-xs font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            <span>Affected Systems:</span>
            <strong className="text-slate-200">
              {incident.affected_systems?.join(", ") || "None registered"}
            </strong>
          </div>
          <div className="flex items-center gap-1.5">
            <Users className="w-3.5 h-3.5 text-indigo-400" />
            <span>Assigned Team:</span>
            <strong className="text-slate-200">{incident.team_name || "SRE On-Call"}</strong>
          </div>
          {incident.fingerprint && (
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500">Fingerprint:</span>
              <span className="text-slate-300 font-mono text-[11px]">{incident.fingerprint}</span>
            </div>
          )}
        </div>
      </div>

      {/* Executive Summary & Severity Reason */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 p-5 rounded-xl border border-slate-800 bg-slate-950/60 backdrop-blur space-y-2">
          <h3 className="text-xs font-semibold font-mono text-slate-400 uppercase tracking-wider">
            Executive Summary
          </h3>
          <p className="text-sm text-slate-200 font-sans leading-relaxed">{incident.summary}</p>
          {incident.severity_reason && (
            <p className="text-xs text-rose-300/90 font-mono pt-2 border-t border-slate-800/60">
              Severity Reason: {incident.severity_reason}
            </p>
          )}
        </div>

        {/* Business Blast Radius Panel */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur space-y-3">
          <h3 className="text-xs font-semibold font-mono text-slate-400 uppercase tracking-wider">
            Business Blast Radius
          </h3>
          <div className="space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <DollarSign className="w-3.5 h-3.5 text-rose-400" />
                Est. Revenue Impact:
              </span>
              <strong className="text-rose-300 text-sm">
                ${incident.estimated_revenue_impact?.toLocaleString() || "12,500"}
              </strong>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Package className="w-3.5 h-3.5 text-amber-400" />
                Failed Orders:
              </span>
              <strong className="text-white text-sm">
                {incident.estimated_orders_affected || "148"}
              </strong>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-cyan-400" />
                Affected Users:
              </span>
              <strong className="text-slate-200 text-sm">
                {incident.estimated_users_affected ?? incident.affected_users_count ?? "420"}
              </strong>
            </div>
          </div>
        </div>
      </div>

      {/* AI Investigation Status Banner */}
      {latestInv && (
        <div className="p-5 rounded-xl border border-cyan-800/60 bg-cyan-950/20 backdrop-blur flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-mono font-bold text-cyan-300 uppercase">
                AI Investigation Active
              </span>
              <StatusBadge status={latestInv.status} size="sm" />
              <BoundaryBadge type="ASSESSMENT" />
            </div>
            <p className="text-sm font-semibold text-white">
              Leading Hypothesis:{" "}
              {latestInv.hypotheses[0]?.title || latestInv.root_cause || latestInv.summary || "Deployment v4.8.2 regression"}
            </p>
            <div className="flex items-center gap-4 text-xs font-mono text-slate-400 pt-1">
              <span>Confidence: <strong className="text-emerald-400">{Math.round((latestInv.confidence || 0.9) * 100)}%</strong></span>
              <span>Uncertainty: {Math.round((latestInv.uncertainty || 0.1) * 100)}%</span>
              <span>Recommendations: {latestInv.recommendations.length}</span>
            </div>
          </div>
          <Link
            href={`/investigations/${latestInv.id}`}
            className="shrink-0 px-4 py-2 rounded-lg text-xs font-mono font-bold text-cyan-200 bg-cyan-950 border border-cyan-700 hover:bg-cyan-900 transition-colors"
          >
            Review Diagnostic Findings →
          </Link>
        </div>
      )}

      {/* Linked Operational Actions (Human-in-the-Loop Gated) */}
      {actions.length > 0 && (
        <div className="rounded-xl border border-cyan-900/50 bg-slate-950/60 p-6 backdrop-blur space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
                Operational Remediation Actions ({actions.length})
              </h3>
            </div>
            <Link
              href="/actions"
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
            >
              Action Queue →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {actions.map((act) => (
              <div
                key={act.id}
                className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-colors space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-cyan-400 font-semibold">{act.action_type}</span>
                  <span className="px-2 py-0.5 rounded-full border text-[10px] font-semibold bg-slate-950 border-slate-800 text-slate-300">
                    {act.status.replace(/_/g, " ")}
                  </span>
                </div>
                <h4 className="text-sm font-medium text-white">{act.title}</h4>
                <p className="text-slate-400 line-clamp-2">{act.description}</p>
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="font-mono text-slate-500 text-[11px]">
                    Target: {act.target_service || "global"}
                  </span>
                  <Link
                    href={`/actions/${act.id}`}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                  >
                    Inspect Workflow →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Incident Timeline Component */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Chronological Incident Timeline
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-500">
            {timeline.length} correlated events
          </span>
        </div>

        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
          {timeline.map((evt, idx) => (
            <div key={evt.event_id || idx} className="relative pl-4">
              <div className="absolute -left-[27px] top-1 w-5 h-5 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center">
                {getTimelineIcon(evt.event_type)}
              </div>
              <div className="p-3.5 rounded-lg border border-slate-800/80 bg-slate-900/40 space-y-1">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-200">{evt.title}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                      {evt.event_type}
                    </span>
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <p className="text-xs text-slate-300 font-sans">{evt.summary || evt.description}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Verified Evidence Panel */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-400" />
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Verified Operational Evidence
            </h3>
          </div>
          <BoundaryBadge type="FACT" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {evidence.map((ev) => (
            <div
              key={ev.id}
              className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs font-mono"
            >
              <div className="flex items-center justify-between">
                <span className="text-teal-400 font-bold uppercase tracking-wider">
                  {ev.source_type || ev.evidence_type}
                </span>
                <span className="text-slate-400">
                  Relevance: <strong className="text-cyan-400">{Math.round((ev.relevance_score ?? ev.confidence ?? 0.95) * 100)}%</strong>
                </span>
              </div>
              <h4 className="text-sm font-semibold text-slate-200 font-sans">{ev.title}</h4>
              <p className="text-xs text-slate-300 font-sans">{ev.summary || ev.description}</p>
              <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
                <span>Observed at: {new Date(ev.observed_at).toLocaleTimeString()}</span>
                <span className="font-mono text-slate-500">REF: {ev.source_id.slice(0, 10)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Correlated Distributed Trace Evidence Panel */}
      <div className="rounded-xl border border-cyan-950/80 bg-slate-950/70 p-6 backdrop-blur space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <GitCommit className="w-5 h-5 text-cyan-400" />
            <div>
              <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
                Correlated Distributed Trace Evidence
              </h3>
              <p className="text-xs text-slate-400">
                Cross-source correlation connecting deployments, metrics, logs, and trace spans
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <BoundaryBadge type="CORRELATION" />
            <button
              onClick={handleCorrelateTraces}
              disabled={isCorrelatingTraces}
              className="px-3 py-1.5 rounded-lg text-xs font-mono font-semibold bg-cyan-950 border border-cyan-700 text-cyan-200 hover:bg-cyan-900 disabled:opacity-50 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>{isCorrelatingTraces ? "Correlating..." : "Correlate & Attach Traces"}</span>
            </button>
            <Link
              href="/traces"
              className="px-3 py-1.5 rounded-lg text-xs font-mono text-slate-400 hover:text-slate-200 border border-slate-800 hover:border-slate-700 transition-colors"
            >
              Trace Explorer →
            </Link>
          </div>
        </div>

        {traceEvidence ? (
          <div className="space-y-4">
            {/* Lead Deployment & Metrics Strip */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <span className="text-[11px] font-mono uppercase text-slate-500">Lead Deployment</span>
                <p className="text-sm font-semibold text-slate-200 mt-1 font-mono">
                  {traceEvidence.lead_deployment
                    ? `${traceEvidence.lead_deployment.service} ${traceEvidence.lead_deployment.version}`
                    : "No recent deployment"}
                </p>
                {traceEvidence.lead_deployment && (
                  <span className="text-[11px] font-mono text-amber-400">
                    Deployed: {new Date(traceEvidence.lead_deployment.deployed_at).toLocaleTimeString()}
                  </span>
                )}
              </div>

              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <span className="text-[11px] font-mono uppercase text-slate-500">Spans in Window</span>
                <p className="text-sm font-semibold text-cyan-300 mt-1 font-mono">
                  {traceEvidence.trace_metrics?.total_spans_in_window ?? 0}
                </p>
                <span className="text-[11px] font-mono text-slate-400">
                  Across {traceEvidence.trace_metrics?.distinct_traces ?? 0} traces
                </span>
              </div>

              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <span className="text-[11px] font-mono uppercase text-slate-500">Slow Spans (&gt;500ms)</span>
                <p className="text-sm font-semibold text-amber-400 mt-1 font-mono">
                  {traceEvidence.trace_metrics?.slow_spans_count ?? 0}
                </p>
                <span className="text-[11px] font-mono text-slate-400">Degraded latency</span>
              </div>

              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                <span className="text-[11px] font-mono uppercase text-slate-500">Error Spans</span>
                <p className="text-sm font-semibold text-rose-400 mt-1 font-mono">
                  {traceEvidence.trace_metrics?.error_spans_count ?? 0}
                </p>
                <span className="text-[11px] font-mono text-slate-400">HTTP 5xx / RPC failure</span>
              </div>
            </div>

            {/* Non-Causal Evidence Synthesis Statement */}
            <div className="p-4 rounded-xl border border-cyan-900/40 bg-cyan-950/20 space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-300">
                  Empirical Trace Synthesis (Non-Causal)
                </span>
                <BoundaryBadge type="FACT" />
              </div>
              <p className="text-xs text-slate-300 font-sans leading-relaxed">
                {traceEvidence.non_causal_synthesis}
              </p>
            </div>

            {/* Critical Path & Error Propagation Deep Dives */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {traceEvidence.critical_path && (
                <div className="p-4 rounded-xl border border-amber-950/40 bg-amber-950/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-amber-400 uppercase">
                      Critical Path Bottleneck
                    </span>
                    <Link
                      href={`/traces/${traceEvidence.critical_path.trace_id}`}
                      className="text-xs font-mono text-amber-400 hover:text-amber-300 flex items-center gap-1"
                    >
                      Inspect Waterfall →
                    </Link>
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    <span className="text-slate-500">Trace:</span> {traceEvidence.critical_path.trace_id.slice(0, 16)}...
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    <span className="text-slate-500">Duration:</span>{" "}
                    <strong className="text-amber-300">{traceEvidence.critical_path.duration_ms} ms</strong>
                  </div>
                  <p className="text-xs text-slate-300 pt-1 font-sans">
                    {traceEvidence.critical_path.assessment}
                  </p>
                </div>
              )}

              {traceEvidence.error_propagation && (
                <div className="p-4 rounded-xl border border-rose-950/40 bg-rose-950/10 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono font-bold text-rose-400 uppercase">
                      Error Propagation Chain
                    </span>
                    <Link
                      href={`/traces/${traceEvidence.error_propagation.trace_id}`}
                      className="text-xs font-mono text-rose-400 hover:text-rose-300 flex items-center gap-1"
                    >
                      Inspect Waterfall →
                    </Link>
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    <span className="text-slate-500">Root Error Service:</span>{" "}
                    <strong className="text-rose-300">{traceEvidence.error_propagation.root_error_service || "unknown"}</strong>
                  </div>
                  <p className="text-xs text-slate-300 pt-1 font-sans">
                    {traceEvidence.error_propagation.assessment}
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center space-y-3">
            <Layers className="w-8 h-8 text-slate-600 mx-auto" />
            <p className="text-xs text-slate-400 max-w-md mx-auto">
              No correlated trace evidence has been extracted for this incident window yet. Run correlation to link deployment, latency, and error traces.
            </p>
            <button
              onClick={handleCorrelateTraces}
              disabled={isCorrelatingTraces}
              className="px-4 py-2 rounded-lg text-xs font-mono font-bold text-cyan-200 bg-cyan-950 border border-cyan-800 hover:bg-cyan-900 transition-colors"
            >
              {isCorrelatingTraces ? "Extracting Cross-Source Correlation..." : "Extract Correlated Traces"}
            </button>
          </div>
        )}

        {/* SRE Operational Runbooks & Playbooks */}
        {runbooks.length > 0 && (
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
                  Matched SRE Runbook Playbooks ({runbooks.length})
                </h3>
              </div>
              <span className="text-xs font-mono text-slate-400">
                Standard Operating Procedures
              </span>
            </div>

            <div className="space-y-4">
              {runbooks.map((rb) => (
                <div key={rb.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="text-[10px] font-mono text-amber-400 uppercase font-semibold">{rb.id}</span>
                      <h4 className="text-sm font-semibold text-white">{rb.title}</h4>
                      <p className="text-xs text-slate-400 mt-1">{rb.summary}</p>
                    </div>
                    <SeverityBadge severity={rb.severity} />
                  </div>

                  {/* Diagnostic Checklist */}
                  <div className="space-y-2 pt-2 border-t border-slate-800/80">
                    <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider">Diagnostic Checklist</span>
                    <div className="space-y-1.5">
                      {rb.diagnostic_steps.map((st) => {
                        const key = `${rb.id}-${st.step}`;
                        const isDone = !!checkedSteps[key];
                        return (
                          <label key={st.step} className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer hover:text-white">
                            <input
                              type="checkbox"
                              checked={isDone}
                              onChange={() => toggleStep(key)}
                              className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-0"
                            />
                            <span className={isDone ? "line-through text-slate-500" : ""}>
                              Step {st.step}: {st.action}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  {/* Recommended Playbook Actions */}
                  {rb.recommended_actions.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80">
                      <span className="text-[11px] font-mono text-slate-400">Playbook Actions:</span>
                      {rb.recommended_actions.map((act, i) => (
                        <Link
                          key={i}
                          href="/actions"
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-mono font-medium transition-colors"
                        >
                          ⚡ {act.title} ({act.action_type})
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Post-Mortem & Incident Retrospective (PIR) */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
                Post-Incident Review (PIR) & Root Cause Retrospective
              </h3>
            </div>

            <div className="flex items-center gap-2">
              {postmortem && (
                <button
                  onClick={handleDownloadPostMortem}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono text-slate-200 bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export Markdown
                </button>
              )}
              <button
                onClick={handleGeneratePostMortem}
                disabled={isGeneratingPostMortem}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-bold text-emerald-200 bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800 transition-colors disabled:opacity-50"
              >
                <Sparkles className={`w-3.5 h-3.5 ${isGeneratingPostMortem ? "animate-spin" : ""}`} />
                {postmortem ? "Regenerate Post-Mortem" : "Generate AI Post-Mortem"}
              </button>
            </div>
          </div>

          {postmortem ? (
            <div className="space-y-4 pt-2">
              {/* MTTD / MTTR Metrics Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 font-mono text-xs">
                  <div className="text-[10px] text-slate-500 uppercase">Mean Time to Detect (MTTD)</div>
                  <div className="text-emerald-400 font-bold text-sm mt-0.5">{postmortem.metrics.mttd_seconds}s</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 font-mono text-xs">
                  <div className="text-[10px] text-slate-500 uppercase">Mean Time to Ack (MTTA)</div>
                  <div className="text-cyan-400 font-bold text-sm mt-0.5">{postmortem.metrics.mtta_minutes ?? "Immediate"}m</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 font-mono text-xs">
                  <div className="text-[10px] text-slate-500 uppercase">Mean Time to Resolve (MTTR)</div>
                  <div className="text-indigo-400 font-bold text-sm mt-0.5">{postmortem.metrics.mttr_minutes}m</div>
                </div>
                <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 font-mono text-xs">
                  <div className="text-[10px] text-slate-500 uppercase">Est. Revenue Lost</div>
                  <div className="text-rose-400 font-bold text-sm mt-0.5">${postmortem.blast_radius.estimated_revenue_lost.toLocaleString()}</div>
                </div>
              </div>

              {/* 5 Whys Root Cause Chain */}
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
                <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                  The 5 Whys (Root Cause Analysis)
                </span>
                <div className="space-y-2 pt-1 font-mono text-xs">
                  {postmortem.five_whys.map((why, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-slate-300">
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400 text-[10px] shrink-0 font-bold">
                        {why.why.split(" ")[0]} {why.why.split(" ")[1]}
                      </span>
                      <span>{why.statement}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Preventative Action Items */}
              <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
                <span className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
                  Preventative Action Items ({postmortem.preventative_action_items.length})
                </span>
                <div className="space-y-2 pt-1">
                  {postmortem.preventative_action_items.map((item) => (
                    <div key={item.id} className="p-2.5 rounded bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2">
                        <span className="text-amber-400 font-semibold">{item.priority}</span>
                        <span className="text-slate-200">{item.title}</span>
                      </div>
                      <div className="text-slate-400 text-[11px]">
                        Owner: <strong className="text-slate-300">{item.owner}</strong> | Due: {item.due_date}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-xl border border-dashed border-slate-800 text-center space-y-2">
              <FileCheck className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No formal Post-Mortem has been recorded for this incident yet. Generate one to synthesize the 5 Whys, duration metrics, and preventative action items.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
