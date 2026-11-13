"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Cpu, Sparkles, AlertTriangle, ArrowRight } from "lucide-react";
import { api } from "@/lib/api/client";
import { Investigation } from "@/lib/api/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BoundaryBadge } from "@/components/ui/BoundaryBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvestigations = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getInvestigations({ limit: 50 });
      setInvestigations(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load investigations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvestigations();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Cpu className="w-3.5 h-3.5" />
            <span>AI OPERATIONS DIAGNOSTICS</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            AI Investigations
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Governed diagnostic sessions evaluating root-cause hypotheses against operational evidence.
          </p>
        </div>
      </div>

      {/* List / Table */}
      {loading ? (
        <TableSkeleton rows={4} cols={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchInvestigations} />
      ) : investigations.length === 0 ? (
        <EmptyState
          title="No AI investigations recorded"
          description="Aegis has not executed any diagnostic sessions yet. Trigger an investigation from an active incident."
        />
      ) : (
        <div className="space-y-4">
          {investigations.map((inv) => {
            const leadingHypo = inv.hypotheses.find((h) => h.status === "SUPPORTED");
            return (
              <div
                key={inv.id}
                className="p-5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-slate-700 transition-colors backdrop-blur space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono font-bold text-slate-200">
                      INV-{inv.id.slice(0, 8)}
                    </span>
                    <StatusBadge status={inv.status} size="sm" />
                    <BoundaryBadge type="ASSESSMENT" />
                  </div>
                  <div className="text-xs font-mono text-slate-400">
                    Started: {new Date(inv.started_at).toLocaleString()}
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-semibold text-white">
                    {leadingHypo?.title || inv.summary || "Operational Diagnostic Session"}
                  </h3>
                  <p className="text-xs text-slate-300 font-sans mt-1 line-clamp-2">
                    {leadingHypo?.description || inv.summary}
                  </p>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs font-mono text-slate-400">
                  <div className="flex flex-wrap items-center gap-4">
                    <span>
                      Confidence:{" "}
                      <strong className="text-emerald-400">
                        {Math.round((inv.confidence || 0.9) * 100)}%
                      </strong>
                    </span>
                    <span>
                      Uncertainty:{" "}
                      <strong className="text-slate-300">
                        {Math.round((inv.uncertainty || 0.1) * 100)}%
                      </strong>
                    </span>
                    <span>
                      Evaluated Hypotheses:{" "}
                      <strong className="text-cyan-400">{inv.hypotheses.length}</strong>
                    </span>
                    <span>
                      Recommendations:{" "}
                      <strong className="text-amber-400">{inv.recommendations.length}</strong>
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href={`/incidents/${inv.incident_id}`}
                      className="text-xs font-mono text-slate-400 hover:text-slate-200"
                    >
                      Incident →
                    </Link>
                    <Link
                      href={`/investigations/${inv.id}`}
                      className="px-3 py-1.5 rounded bg-slate-900 border border-slate-800 text-cyan-400 hover:bg-slate-800 transition-colors inline-flex items-center gap-1.5 font-bold"
                    >
                      <span>Review Findings</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
