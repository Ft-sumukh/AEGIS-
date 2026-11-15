"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Radio,
  AlertTriangle,
  Play,
  RotateCcw,
  ShieldAlert,
  Activity,
  Layers,
  ArrowRight,
  CheckCircle,
  Clock,
  Sparkles,
} from "lucide-react";

import { api } from "@/lib/api/client";
import { ChaosScenario, ChaosRun } from "@/lib/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { useAuth } from "@/lib/auth/AuthContext";
import { useLiveEvents } from "@/lib/hooks/useLiveEvents";

export default function ChaosLabPage() {
  const { role } = useAuth();
  const [scenarios, setScenarios] = useState<ChaosScenario[]>([]);
  const [activeRuns, setActiveRuns] = useState<ChaosRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [injectingId, setInjectingId] = useState<string | null>(null);
  const [recoveringId, setRecoveringId] = useState<string | null>(null);
  const [message, setMessage] = useState<{ text: string; type: "success" | "error" } | null>(null);

  const { lastEvent } = useLiveEvents();

  const loadData = async () => {
    try {
      const [scenList, runList] = await Promise.all([
        api.listChaosScenarios(),
        api.listActiveChaosRuns(),
      ]);
      setScenarios(scenList);
      setActiveRuns(runList);
    } catch {
      // Quiet fallback
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Refresh if live chaos event arrives
  useEffect(() => {
    if (
      lastEvent?.type === "CHAOS_FAULT_INJECTED" ||
      lastEvent?.type === "CHAOS_FAULT_RECOVERED"
    ) {
      loadData();
    }
  }, [lastEvent]);

  const handleInject = async (scenarioId: string) => {
    setInjectingId(scenarioId);
    setMessage(null);
    try {
      const run = await api.injectChaosFault(scenarioId);
      setMessage({
        text: `Injected fault for ${run.scenario.name} (Run ID: ${run.run_id})`,
        type: "success",
      });
      await loadData();
    } catch (err: any) {
      setMessage({
        text: err?.message || "Failed to inject chaos fault",
        type: "error",
      });
    } finally {
      setInjectingId(null);
    }
  };

  const handleRecover = async (runId: string) => {
    setRecoveringId(runId);
    setMessage(null);
    try {
      await api.recoverChaosFault(runId);
      setMessage({
        text: `Baseline telemetry restored for run ${runId}`,
        type: "success",
      });
      await loadData();
    } catch (err: any) {
      setMessage({
        text: err?.message || "Failed to recover baseline",
        type: "error",
      });
    } finally {
      setRecoveringId(null);
    }
  };

  const isOperator = role === "OPERATOR" || role === "ADMIN";
  const activeFaults = activeRuns.filter((r) => r.status === "ACTIVE_FAULT");

  return (
    <AppShell>
      <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-950/60 border border-rose-800/60 flex items-center justify-center text-rose-400">
                <Radio className="w-5 h-5 animate-pulse" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                  Chaos Engineering Lab
                </h1>
                <p className="text-sm text-slate-400 font-mono">
                  Controlled Synthetic Fault Injection & Closed-Loop Resilience Evaluation
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400 border border-slate-800 bg-slate-900/60 px-3 py-1.5 rounded-lg">
              Mode: <strong className="text-cyan-400 font-semibold">SIMULATED SAFEHOUSE</strong>
            </span>
          </div>
        </div>

        {/* Feedback Alert */}
        {message && (
          <div
            className={`p-4 rounded-xl border text-sm font-mono flex items-center justify-between ${
              message.type === "success"
                ? "bg-emerald-950/40 border-emerald-800/80 text-emerald-300"
                : "bg-rose-950/40 border-rose-800/80 text-rose-300"
            }`}
          >
            <div className="flex items-center gap-2">
              {message.type === "success" ? (
                <CheckCircle className="w-4 h-4 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400" />
              )}
              <span>{message.text}</span>
            </div>
            <button
              onClick={() => setMessage(null)}
              className="text-slate-400 hover:text-slate-200 text-xs"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Active Fault Monitor Banner */}
        {activeFaults.length > 0 && (
          <div className="rounded-xl border border-rose-800/80 bg-rose-950/20 p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 animate-ping" />
                <h3 className="font-bold text-rose-200 text-sm font-mono tracking-wide">
                  ACTIVE CHAOS EXPERIMENT IN PROGRESS ({activeFaults.length})
                </h3>
              </div>
              <span className="text-xs font-mono text-rose-400">
                Aegis Anomaly Detectors & Incident Correlators Engaged
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {activeFaults.map((run) => (
                <div
                  key={run.run_id}
                  className="rounded-lg border border-rose-900/80 bg-slate-950/80 p-4 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-400">{run.run_id}</span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-rose-950 text-rose-300 border border-rose-800">
                      ACTIVE FAULT
                    </span>
                  </div>

                  <div>
                    <h4 className="text-sm font-semibold text-slate-100">
                      {run.scenario.name}
                    </h4>
                    <p className="text-xs text-slate-400 mt-1 font-mono">
                      Target: <strong className="text-cyan-400">{run.scenario.target_service}</strong> | Injected Value:{" "}
                      <strong className="text-rose-400">
                        {run.scenario.fault_value} {run.scenario.unit}
                      </strong>{" "}
                      (Baseline: {run.scenario.baseline_value} {run.scenario.unit})
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                    <div className="text-[11px] font-mono text-slate-400">
                      Recommended: <strong className="text-amber-400">{run.scenario.recommended_action}</strong>
                    </div>

                    <button
                      onClick={() => handleRecover(run.run_id)}
                      disabled={!isOperator || recoveringId === run.run_id}
                      className="flex items-center gap-1.5 px-3 py-1 rounded bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-800/80 text-emerald-300 text-xs font-mono font-semibold transition-colors disabled:opacity-50"
                    >
                      <RotateCcw className={`w-3.5 h-3.5 ${recoveringId === run.run_id ? "animate-spin" : ""}`} />
                      Restore Baseline
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scenarios Catalog */}
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Fault Injection Scenarios</h2>
            <p className="text-xs font-mono text-slate-400">
              Select a production failure scenario to simulate telemetry degradation and observe closed-loop mitigation.
            </p>
          </div>

          {loading ? (
            <LoadingSkeleton rows={4} />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {scenarios.map((scen) => {
                const isActive = activeFaults.some((r) => r.scenario.id === scen.id);

                return (
                  <div
                    key={scen.id}
                    className={`rounded-xl border p-5 flex flex-col justify-between transition-all ${
                      isActive
                        ? "border-rose-800/80 bg-rose-950/10 shadow-lg shadow-rose-950/20"
                        : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
                    }`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <span className="text-[11px] font-mono text-slate-500 uppercase tracking-wider">
                            {scen.id}
                          </span>
                          <h3 className="text-base font-semibold text-slate-100 mt-0.5">
                            {scen.name}
                          </h3>
                        </div>
                        <SeverityBadge severity={scen.risk_level as any} />
                      </div>

                      <p className="text-xs text-slate-400 leading-relaxed">
                        {scen.description}
                      </p>

                      {/* Telemetry Metric Comparison */}
                      <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 font-mono text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Baseline Metric</div>
                          <div className="text-emerald-400 font-semibold mt-0.5">
                            {scen.baseline_value} {scen.unit}
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Fault Injection</div>
                          <div className="text-rose-400 font-semibold mt-0.5">
                            {scen.fault_value} {scen.unit}
                          </div>
                        </div>
                      </div>

                      <div className="text-xs font-mono text-slate-400 flex items-center gap-2">
                        <Layers className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Target Service: <strong className="text-slate-200">{scen.target_service}</strong></span>
                      </div>
                    </div>

                    <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between">
                      <div className="text-[11px] font-mono text-slate-400">
                        Remediation: <span className="text-amber-400">{scen.recommended_action}</span>
                      </div>

                      <button
                        onClick={() => handleInject(scen.id)}
                        disabled={!isOperator || injectingId === scen.id || isActive}
                        className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-mono font-semibold transition-colors ${
                          isActive
                            ? "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
                            : "bg-rose-950/80 hover:bg-rose-900 border border-rose-800 text-rose-200"
                        } disabled:opacity-50`}
                      >
                        <Play className={`w-3.5 h-3.5 ${injectingId === scen.id ? "animate-spin" : ""}`} />
                        {isActive ? "Active" : "Inject Fault"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
