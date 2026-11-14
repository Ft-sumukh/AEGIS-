"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Layers, Server, ArrowRight, GitBranch, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api/client";
import { SystemHealth } from "@/lib/api/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function SystemsPage() {
  const [systems, setSystems] = useState<SystemHealth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSystems = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSystems();
      setSystems(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load systems health");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystems();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Layers className="w-3.5 h-3.5" />
            <span>INFRASTRUCTURE & SERVICE TOPOLOGY</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Systems & Services
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Operational availability, latencies, deployment status, and error postures across architecture.
          </p>
        </div>
      </div>

      {loading ? (
        <CardSkeleton count={6} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchSystems} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {systems.map((sys) => {
            const isCritical = sys.status === "CRITICAL";
            const isDegraded = sys.status === "DEGRADED";

            return (
              <div
                key={sys.name}
                className={`p-5 rounded-xl border backdrop-blur space-y-4 transition-all hover:border-slate-700 ${
                  isCritical
                    ? "border-rose-900/60 bg-rose-950/10"
                    : isDegraded
                    ? "border-amber-900/60 bg-amber-950/10"
                    : "border-slate-800 bg-slate-950/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Server className="w-4 h-4 text-slate-400" />
                    <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                      {sys.category}
                    </span>
                  </div>
                  <StatusBadge status={sys.status} size="sm" />
                </div>

                <div>
                  <h3 className="text-base font-bold font-mono text-white tracking-tight">
                    {sys.name}
                  </h3>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                  <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40">
                    <div className="text-[10px] text-slate-400 uppercase">Avg Latency</div>
                    <div className="text-sm font-bold text-slate-200 mt-0.5">
                      {sys.latency_ms}ms
                    </div>
                  </div>
                  <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40">
                    <div className="text-[10px] text-slate-400 uppercase">Error Rate</div>
                    <div
                      className={`text-sm font-bold mt-0.5 ${
                        sys.error_rate > 1.0 ? "text-rose-400" : "text-emerald-400"
                      }`}
                    >
                      {sys.error_rate.toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono text-slate-400">
                  <div className="flex items-center gap-1.5">
                    <GitBranch className="w-3.5 h-3.5 text-amber-400" />
                    <span>{sys.last_deployment?.version || "v4.8.0"}</span>
                  </div>

                  <Link
                    href={`/systems/${sys.name}`}
                    className="text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1 font-bold"
                  >
                    <span>Topology</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
