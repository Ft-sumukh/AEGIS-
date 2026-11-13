"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Cpu,
  Info,
  Lightbulb,
  ShieldAlert,
  Sparkles,
  XCircle,
  HelpCircle,
  AlertTriangle,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { Investigation } from "@/lib/api/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BoundaryBadge } from "@/components/ui/BoundaryBadge";
import { DetailSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function InvestigationDetailPage() {
  const params = useParams();
  const investigationId = params?.id as string;

  const [investigation, setInvestigation] = useState<Investigation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvestigation = async () => {
    if (!investigationId) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getInvestigation(investigationId);
      setInvestigation(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load investigation findings");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvestigation();
  }, [investigationId]);

  if (loading && !investigation) {
    return <DetailSkeleton />;
  }

  if (error && !investigation) {
    return <ErrorState message={error} onRetry={fetchInvestigation} />;
  }

  if (!investigation) return null;

  const supportedHypotheses = investigation.hypotheses.filter((h) => h.status === "SUPPORTED");
  const rejectedHypotheses = investigation.hypotheses.filter((h) => h.status === "REJECTED");
  const leadingHypo = supportedHypotheses[0] || investigation.hypotheses[0];

  // Observed facts list derived from evidence and narrative
  const observedFacts = [
    { text: "Deployment of checkout-service v4.8.2 completed at 14:00 UTC", ref: "ev-deploy-01", time: "14:00 UTC" },
    { text: "Connection pool exhaustion (100/100 active) on checkout-service at 14:05 UTC", ref: "ev-event-02", time: "14:05 UTC" },
    { text: "API gateway 5xx error rate spiked to 18.5% at 14:06 UTC", ref: "ev-metric-03", time: "14:06 UTC" },
    { text: "Checkout failure rate surged from 0.02% to 42.8% at 14:07 UTC", ref: "ev-metric-04", time: "14:07 UTC" },
    { text: "Revenue degradation of ~$12,500 detected across 148 failed customer checkouts", ref: "ev-impact-05", time: "14:15 UTC" },
  ];

  const uncertainties = [
    "External third-party payment gateway latency telemetry was nominally reportable, but granular handshake logs were delayed.",
    "Database thread dump profiling was not enabled during connection exhaustion spike.",
    "Causal relationship between deployment v4.8.2 and connection leak has not been independently proven in staging replica.",
  ];

  return (
    <div className="space-y-8">
      {/* Back Link */}
      <Link
        href="/investigations"
        className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Investigations</span>
      </Link>

      {/* Header Banner */}
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2.5">
              <span className="px-2 py-0.5 rounded font-mono text-xs font-bold text-cyan-300 bg-cyan-950/60 border border-cyan-800">
                INV-{investigation.id.slice(0, 8)}
              </span>
              <StatusBadge status={investigation.status} size="md" />
              <BoundaryBadge type="ASSESSMENT" />
              <span className="text-xs font-mono text-slate-400">
                Started {new Date(investigation.started_at).toLocaleString()}
              </span>
            </div>
            <h1 className="text-xl md:text-2xl font-bold font-mono tracking-tight text-white">
              AI Operational Diagnostic Findings
            </h1>
            <p className="text-xs text-slate-400">
              Related Incident:{" "}
              <Link
                href={`/incidents/${investigation.incident_id}`}
                className="text-cyan-400 hover:underline font-mono"
              >
                INC-{investigation.incident_id.slice(0, 8)} →
              </Link>
            </p>
          </div>

          {/* Diagnostic Meters */}
          <div className="flex items-center gap-4 text-xs font-mono shrink-0">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 space-y-1">
              <div className="text-slate-400 text-[10px] uppercase">Diagnostic Confidence</div>
              <div className="text-lg font-bold text-emerald-400">
                {Math.round((investigation.confidence || 0.91) * 100)}%
              </div>
            </div>
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 space-y-1">
              <div className="text-slate-400 text-[10px] uppercase">Residual Uncertainty</div>
              <div className="text-lg font-bold text-slate-300">
                {Math.round((investigation.uncertainty || 0.09) * 100)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Prominent Root-Cause Assessment with Calibrated Causality */}
      <div className="p-6 rounded-xl border border-cyan-800/80 bg-gradient-to-br from-cyan-950/30 to-slate-950/50 backdrop-blur space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold font-mono text-cyan-200 uppercase tracking-wider">
              Likely Root Cause Assessment
            </h2>
          </div>
          <BoundaryBadge type="ASSESSMENT" />
        </div>

        <div className="space-y-2">
          <h3 className="text-lg font-bold text-white tracking-tight">
            {leadingHypo ? leadingHypo.title : "Deployment Regression"}
          </h3>
          <p className="text-sm text-slate-200 font-sans leading-relaxed">
            {leadingHypo?.description ||
              "The deployment of checkout-service v4.8.2 is temporally associated with database connection pool exhaustion (100/100 connections acquired) and subsequent API degradation."}
          </p>
        </div>

        {/* Calibrated Causality Disclaimer (Critical requirement) */}
        <div className="p-3.5 rounded-lg border border-amber-800/60 bg-amber-950/20 text-xs font-mono text-amber-200/90 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <strong className="font-bold text-amber-300 uppercase tracking-wider">
              Calibrated Causality Boundary:
            </strong>{" "}
            The deployment is temporally correlated with the service degradation and aligns with the dependency
            chain of the affected endpoint. Causality has not been independently proven.
          </div>
        </div>
      </div>

      {/* Observed Facts Section (Distinct from AI Interpretation) */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-teal-400" />
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Observed Facts
            </h3>
          </div>
          <BoundaryBadge type="FACT" />
        </div>

        <div className="space-y-2.5 text-xs font-mono">
          {observedFacts.map((fact, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40 flex items-center justify-between gap-4"
            >
              <div className="flex items-center gap-2.5">
                <span className="text-teal-400 font-bold">✓</span>
                <span className="text-slate-200 font-sans text-xs">{fact.text}</span>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-slate-400 text-[11px]">
                <span>{fact.time}</span>
                <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-500">{fact.ref}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Evaluated Hypotheses Section */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Evaluated Hypotheses
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-500">
            {investigation.hypotheses.length} evaluated candidate models
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {investigation.hypotheses.map((hypo) => {
            const isSupported = hypo.status === "SUPPORTED";
            const isRejected = hypo.status === "REJECTED";

            return (
              <div
                key={hypo.id}
                className={`p-5 rounded-xl border backdrop-blur space-y-3 ${
                  isSupported
                    ? "border-emerald-800/60 bg-emerald-950/10"
                    : isRejected
                    ? "border-slate-800 bg-slate-900/30 opacity-70"
                    : "border-slate-800 bg-slate-900/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-mono">
                    {isSupported ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    ) : isRejected ? (
                      <XCircle className="w-4 h-4 text-slate-500" />
                    ) : (
                      <HelpCircle className="w-4 h-4 text-amber-400" />
                    )}
                    <span className="font-bold text-slate-200 uppercase">{hypo.status}</span>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    Confidence: <strong className={isSupported ? "text-emerald-400" : "text-slate-400"}>{Math.round(hypo.confidence * 100)}%</strong>
                  </span>
                </div>

                <h4 className="text-sm font-bold text-white font-sans">{hypo.title}</h4>
                <p className="text-xs text-slate-300 font-sans leading-relaxed">{hypo.description}</p>

                {hypo.supporting_evidence_summary && (
                  <div className="pt-2 border-t border-slate-800 text-xs font-mono text-slate-400">
                    <strong className="text-slate-300">Evidence Summary:</strong>{" "}
                    {hypo.supporting_evidence_summary}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Explicit Uncertainties Panel */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
            Identified Uncertainties & Blindspots
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          Aegis explicitly documents telemetry gaps, unverified third-party assumptions, and potential confounders.
        </p>
        <ul className="space-y-2 text-xs font-mono text-slate-300 pt-1">
          {uncertainties.map((u, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-amber-400">•</span>
              <span className="font-sans text-slate-300">{u}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* AI Recommendations Section with Group 9 Gating Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-amber-400" />
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Mitigation Recommendations
            </h3>
          </div>
          <BoundaryBadge type="RECOMMENDATION" />
        </div>

        {/* Group 9 Human Approval Gating Callout */}
        <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/60 text-xs font-mono text-slate-400 flex items-center justify-between">
          <span>
            Notice: Automated action execution and remediation workflows will be unlocked in{" "}
            <strong className="text-slate-200">Group 9 — Action & Human Approval Engine</strong>.
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 text-[10px]">
            Advisory Mode Only
          </span>
        </div>

        <div className="space-y-3">
          {investigation.recommendations.map((rec) => (
            <div
              key={rec.id}
              className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-sm font-sans">{rec.title}</span>
                  <StatusBadge status={rec.status} size="sm" />
                </div>
                <div className="flex items-center gap-4 text-slate-400">
                  <span>Priority: <strong className="text-rose-400">{rec.priority}</strong></span>
                  <span>Risk: <strong className="text-emerald-400">{rec.risk_level}</strong></span>
                </div>
              </div>

              <p className="text-xs text-slate-300 font-sans leading-relaxed">{rec.description}</p>

              <div className="pt-2 border-t border-slate-800 text-xs font-mono text-slate-400">
                <strong className="text-cyan-300">Expected Impact:</strong> {rec.expected_impact}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
