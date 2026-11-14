"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  GitBranch,
  Layers,
  Server,
  AlertTriangle,
  Clock,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { SystemDetail } from "@/lib/api/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DetailSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function SystemDetailPage() {
  const params = useParams();
  const systemName = params?.id as string;

  const [system, setSystem] = useState<SystemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSystem = async () => {
    if (!systemName) return;
    try {
      setLoading(true);
      setError(null);
      const res = await api.getSystem(systemName);
      setSystem(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load system detail");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystem();
  }, [systemName]);

  if (loading && !system) return <DetailSkeleton />;
  if (error && !system) return <ErrorState message={error} onRetry={fetchSystem} />;
  if (!system) return null;

  return (
    <div className="space-y-8">
      {/* Back Link */}
      <Link
        href="/systems"
        className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        <span>Back to Systems</span>
      </Link>

      {/* Header Banner */}
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 backdrop-blur space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <span className="text-xs font-mono uppercase text-slate-400 font-bold">
                {system.category}
              </span>
              <StatusBadge status={system.status} size="md" />
            </div>
            <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
              {system.name}
            </h1>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono shrink-0">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 text-right">
              <div className="text-[10px] text-slate-400 uppercase">Latency</div>
              <div className="text-lg font-bold text-slate-200">{system.latency_ms}ms</div>
            </div>
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 text-right">
              <div className="text-[10px] text-slate-400 uppercase">Error Rate</div>
              <div
                className={`text-lg font-bold ${
                  system.error_rate > 1.0 ? "text-rose-400" : "text-emerald-400"
                }`}
              >
                {system.error_rate.toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Service Dependency Topology */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-6 backdrop-blur space-y-4">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
            Architecture Dependency Chain
          </h3>
        </div>

        <div className="p-6 rounded-xl border border-slate-800/80 bg-slate-900/30 flex flex-col md:flex-row items-center justify-between gap-4 text-xs font-mono">
          {/* Upstream */}
          <div className="flex-1 w-full text-center space-y-2">
            <div className="text-[10px] uppercase text-slate-500 font-bold">Upstream Dependencies</div>
            <div className="space-y-1.5">
              {system.dependencies.upstream.length > 0 ? (
                system.dependencies.upstream.map((up) => (
                  <div
                    key={up}
                    className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-300"
                  >
                    {up}
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic">None (Edge Gateway)</div>
              )}
            </div>
          </div>

          <div className="text-slate-600 hidden md:block">→</div>

          {/* Current Node */}
          <div className="flex-1 w-full text-center p-4 rounded-xl bg-cyan-950/40 border border-cyan-700/60 shadow-[0_0_15px_rgba(6,182,212,0.15)]">
            <div className="text-[10px] uppercase text-cyan-400 font-bold">This Service</div>
            <div className="text-base font-bold text-white mt-1">{system.name}</div>
            <div className="text-[11px] text-cyan-300 mt-0.5">{system.status}</div>
          </div>

          <div className="text-slate-600 hidden md:block">→</div>

          {/* Downstream */}
          <div className="flex-1 w-full text-center space-y-2">
            <div className="text-[10px] uppercase text-slate-500 font-bold">Downstream Dependencies</div>
            <div className="space-y-1.5">
              {system.dependencies.downstream.length > 0 ? (
                system.dependencies.downstream.map((dn) => (
                  <div
                    key={dn}
                    className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-300"
                  >
                    {dn}
                  </div>
                ))
              ) : (
                <div className="text-slate-500 italic">None (Terminal Storage)</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Deployments & System Events */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Recent Deployments */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 backdrop-blur space-y-3">
          <div className="flex items-center gap-2">
            <GitBranch className="w-4 h-4 text-amber-400" />
            <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Recent Deployments
            </h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            {system.recent_deployments.length > 0 ? (
              system.recent_deployments.map((d) => (
                <div
                  key={d.id}
                  className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40 flex items-center justify-between"
                >
                  <div>
                    <div className="font-bold text-white">{d.version}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Deployed by {d.deployed_by}
                    </div>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={d.status} size="sm" />
                    <div className="text-[10px] text-slate-500 mt-1">
                      {new Date(d.deployed_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-slate-500 font-mono">
                No recent deployment events recorded
              </div>
            )}
          </div>
        </div>

        {/* Related Incidents */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-5 backdrop-blur space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Impacting Operational Incidents
            </h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            {system.related_incidents.length > 0 ? (
              system.related_incidents.map((inc) => (
                <Link
                  key={inc.id}
                  href={`/incidents/${inc.id}`}
                  className="p-3 rounded-lg border border-slate-800/80 bg-slate-900/40 block hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white font-sans text-xs">{inc.title}</span>
                    <StatusBadge status={inc.status} size="sm" />
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Detected {new Date(inc.detected_at).toLocaleString()}
                  </div>
                </Link>
              ))
            ) : (
              <div className="p-4 text-center text-xs text-slate-500 font-mono">
                No active incidents affecting this system
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
