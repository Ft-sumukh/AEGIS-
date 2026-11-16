"use client";

import React, { useEffect, useState } from "react";
import {
  Gauge,
  Flame,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Plus,
  Play,
  ShieldAlert,
  Sliders,
  TrendingDown,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { ServiceLevelObjective, SLOSummary, SLOStatus } from "@/lib/api/types";

export default function SLOsPage() {
  const [slos, setSlos] = useState<ServiceLevelObjective[]>([]);
  const [summary, setSummary] = useState<SLOSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [evaluatingId, setEvaluatingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("ALL");

  // New SLO Form state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newSlo, setNewSlo] = useState({
    name: "",
    service_name: "checkout-service",
    description: "",
    target_percentage: 99.9,
    sli_metric_name: "api_error_rate",
    sli_type: "AVAILABILITY",
    time_window_days: 30,
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [sloList, summaryRes] = await Promise.all([
        api.getSLOs(),
        api.getSLOSummary(),
      ]);
      setSlos(sloList);
      setSummary(summaryRes);
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to load SLO metrics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000);
    return () => clearInterval(interval);
  }, []);

  const handleSimulateEvaluation = async (sloId: string, errorRate: number) => {
    try {
      setEvaluatingId(sloId);
      const updated = await api.evaluateSLO(sloId, errorRate);
      setSlos((prev) => prev.map((s) => (s.id === sloId ? updated : s)));
      // Refresh summary
      const sum = await api.getSLOSummary();
      setSummary(sum);
    } catch (err: any) {
      alert(`Simulation error: ${err.message}`);
    } finally {
      setEvaluatingId(null);
    }
  };

  const handleCreateSLO = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const created = await api.createSLO(newSlo);
      setSlos((prev) => [created, ...prev]);
      setShowCreateModal(false);
      setNewSlo({
        name: "",
        service_name: "checkout-service",
        description: "",
        target_percentage: 99.9,
        sli_metric_name: "api_error_rate",
        sli_type: "AVAILABILITY",
        time_window_days: 30,
      });
      loadData();
    } catch (err: any) {
      alert(`Failed to create SLO: ${err.message}`);
    }
  };

  const filteredSlos = slos.filter((s) => {
    if (filterStatus === "ALL") return true;
    return s.status === filterStatus;
  });

  const getStatusBadge = (status: SLOStatus) => {
    switch (status) {
      case "HEALTHY":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
            <CheckCircle2 className="w-3.5 h-3.5" /> Healthy
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-amber-950/60 text-amber-300 border border-amber-800/60">
            <AlertTriangle className="w-3.5 h-3.5" /> Warning
          </span>
        );
      case "BURNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-rose-950/80 text-rose-300 border border-rose-800 animate-pulse">
            <Flame className="w-3.5 h-3.5 text-rose-400" /> Burning Fast
          </span>
        );
      case "EXHAUSTED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-red-950 text-red-200 border border-red-700">
            <ShieldAlert className="w-3.5 h-3.5 text-red-400" /> Budget Exhausted
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Gauge className="w-3.5 h-3.5" />
            <span>GOOGLE SRE ERROR BUDGET BURNING ENGINE</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            SLOs & Multi-Window Error Budgets
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            1h/6h/24h multi-window burn-rate velocity alerting and time-to-exhaustion forecasting.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-900 border border-slate-800 rounded hover:bg-slate-800 transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-500 transition shadow"
          >
            <Plus className="w-3.5 h-3.5" />
            Define SLO
          </button>
        </div>
      </div>

      {/* SRE Google Standard Burn Rate Alert Explainer */}
      <div className="p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 flex items-start gap-3">
        <Sliders className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-slate-200">
            Multi-Window Multi-Burn-Rate Alerting Standard (Google SRE Handbook)
          </p>
          <p className="text-slate-400 leading-relaxed">
            A burn rate of <span className="text-emerald-300 font-mono">1.0x</span> consumes exactly 100% of the error budget over 30 days.
            A 1-hour burn rate of <span className="text-rose-400 font-bold font-mono">14.4x</span> consumes 2% of the entire monthly budget in 60 minutes and triggers an immediate paging alert.
            A 6-hour burn rate of <span className="text-amber-300 font-bold font-mono">6.0x</span> triggers high-priority ticket escalation.
          </p>
        </div>
      </div>

      {/* KPI Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800">
          <div className="text-xs text-slate-400 uppercase tracking-wider font-medium">Monitored SLOs</div>
          <div className="text-2xl font-bold text-slate-100 mt-1">{summary?.total_slos ?? 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Tier-1 & Tier-2 services</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800">
          <div className="text-xs text-emerald-400 uppercase tracking-wider font-medium">Healthy</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{summary?.healthy_count ?? 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Burn rate &le; 1.0x</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800">
          <div className="text-xs text-amber-400 uppercase tracking-wider font-medium">Warning</div>
          <div className="text-2xl font-bold text-amber-300 mt-1">{summary?.warning_count ?? 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Burn rate &ge; 4.0x</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800">
          <div className="text-xs text-rose-400 uppercase tracking-wider font-medium">Burning Critical</div>
          <div className="text-2xl font-bold text-rose-400 mt-1">{summary?.burning_count ?? 0}</div>
          <div className="text-[11px] text-slate-500 mt-1">Paging threshold (&ge; 14.4x)</div>
        </div>
        <div className="p-4 rounded-lg bg-slate-900/70 border border-slate-800">
          <div className="text-xs text-indigo-400 uppercase tracking-wider font-medium">Avg Budget Left</div>
          <div className="text-2xl font-bold text-indigo-300 mt-1">
            {summary?.average_error_budget_percent ?? 100}%
          </div>
          <div className="text-[11px] text-slate-500 mt-1">Aggregated across org</div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        {["ALL", "HEALTHY", "WARNING", "BURNING", "EXHAUSTED"].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilterStatus(tab)}
            className={`px-3 py-1 rounded text-xs font-medium transition ${
              filterStatus === tab
                ? "bg-slate-800 text-white border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* SLO Inventory List */}
      {loading && slos.length === 0 ? (
        <div className="py-16 text-center text-slate-500 text-sm">Evaluating operational telemetry...</div>
      ) : filteredSlos.length === 0 ? (
        <div className="py-12 text-center text-slate-500 text-sm bg-slate-900/30 rounded border border-slate-800">
          No Service Level Objectives match the selected filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {filteredSlos.map((slo) => {
            const isEvaluating = evaluatingId === slo.id;
            const budgetPercent = slo.error_budget_remaining_percent;
            const budgetColor =
              budgetPercent > 70
                ? "bg-emerald-500"
                : budgetPercent > 25
                ? "bg-amber-500"
                : "bg-rose-500";

            return (
              <div
                key={slo.id}
                className="p-5 rounded-lg bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition space-y-4"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="text-base font-semibold text-slate-100">{slo.name}</h3>
                      {getStatusBadge(slo.status)}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                      <span>Service: <strong className="text-slate-200 font-mono">{slo.service_name}</strong></span>
                      <span>•</span>
                      <span>Target: <strong className="text-slate-200">{slo.target_percentage}%</strong></span>
                      <span>•</span>
                      <span>Current SLI: <strong className="text-emerald-400">{slo.current_sli}%</strong></span>
                      <span>•</span>
                      <span>Window: {slo.time_window_days} Days</span>
                    </div>
                    {slo.description && (
                      <p className="text-xs text-slate-400 mt-1 max-w-2xl">{slo.description}</p>
                    )}
                  </div>

                  {/* Interactive Simulation Controls */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSimulateEvaluation(slo.id, 0.01)}
                      disabled={isEvaluating}
                      title="Simulate normal low error rate (0.01%)"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-emerald-300 bg-emerald-950/40 border border-emerald-800/50 rounded hover:bg-emerald-900/50 transition"
                    >
                      <CheckCircle2 className="w-3 h-3" /> Nominal
                    </button>
                    <button
                      onClick={() => handleSimulateEvaluation(slo.id, 4.8)}
                      disabled={isEvaluating}
                      title="Simulate severe 4.8% error rate spike (Triggers 14.4x paging burn rate)"
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-rose-300 bg-rose-950/40 border border-rose-800/60 rounded hover:bg-rose-900/50 transition"
                    >
                      <Flame className="w-3 h-3 text-rose-400" /> Simulate Spike
                    </button>
                  </div>
                </div>

                {/* Error Budget Progress Bar */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 font-medium">Error Budget Remaining</span>
                    <span className="font-mono font-semibold text-slate-200">
                      {slo.error_budget_remaining_percent}%
                    </span>
                  </div>
                  <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                    <div
                      className={`h-full ${budgetColor} transition-all duration-500 rounded-full`}
                      style={{ width: `${Math.min(100, Math.max(0, budgetPercent))}%` }}
                    />
                  </div>
                </div>

                {/* Multi-Window Burn Rates and Time To Exhaustion */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2 border-t border-slate-800/60 text-xs">
                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/50">
                    <div className="text-slate-400">1-Hour Burn Rate</div>
                    <div className="text-sm font-mono font-bold mt-0.5 text-slate-100">
                      {slo.burn_rate_1h}x
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {slo.burn_rate_1h >= 14.4 ? "🚨 Immediate Page" : "Within envelope"}
                    </div>
                  </div>

                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/50">
                    <div className="text-slate-400">6-Hour Burn Rate</div>
                    <div className="text-sm font-mono font-bold mt-0.5 text-slate-100">
                      {slo.burn_rate_6h}x
                    </div>
                    <div className="text-[10px] text-slate-500">Medium window</div>
                  </div>

                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/50">
                    <div className="text-slate-400">24-Hour Burn Rate</div>
                    <div className="text-sm font-mono font-bold mt-0.5 text-slate-100">
                      {slo.burn_rate_24h}x
                    </div>
                    <div className="text-[10px] text-slate-500">Long window</div>
                  </div>

                  <div className="p-2 rounded bg-slate-950/50 border border-slate-800/50">
                    <div className="text-slate-400">Time-to-Exhaustion</div>
                    <div className="text-sm font-mono font-bold mt-0.5 text-slate-100 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      {slo.time_to_exhaustion_hours ? `${slo.time_to_exhaustion_hours} hrs` : "Nominal (>30d)"}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {slo.time_to_exhaustion_hours && slo.time_to_exhaustion_hours < 24 ? "⚠️ Imminent breach" : "Budget safe"}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create SLO Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-lg max-w-lg w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Gauge className="w-5 h-5 text-indigo-400" />
              Define New Service Level Objective
            </h3>
            <form onSubmit={handleCreateSLO} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">SLO Name</label>
                <input
                  type="text"
                  required
                  value={newSlo.name}
                  onChange={(e) => setNewSlo({ ...newSlo, name: e.target.value })}
                  placeholder="e.g. Ingress API Availability"
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Target Service</label>
                  <input
                    type="text"
                    required
                    value={newSlo.service_name}
                    onChange={(e) => setNewSlo({ ...newSlo, service_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Target Objective (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="90"
                    max="99.999"
                    required
                    value={newSlo.target_percentage}
                    onChange={(e) => setNewSlo({ ...newSlo, target_percentage: parseFloat(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">SLI Metric Identifier</label>
                  <input
                    type="text"
                    required
                    value={newSlo.sli_metric_name}
                    onChange={(e) => setNewSlo({ ...newSlo, sli_metric_name: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Window (Days)</label>
                  <input
                    type="number"
                    min="7"
                    max="90"
                    value={newSlo.time_window_days}
                    onChange={(e) => setNewSlo({ ...newSlo, time_window_days: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                  />
                </div>
              </div>
              <div>
                <label className="block text-slate-300 font-medium mb-1">Description / Business Context</label>
                <textarea
                  rows={2}
                  value={newSlo.description}
                  onChange={(e) => setNewSlo({ ...newSlo, description: e.target.value })}
                  placeholder="Describes customer-facing implications if this budget exhausts..."
                  className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-slate-200 focus:border-indigo-500 outline-none"
                />
              </div>
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3 py-1.5 text-slate-400 hover:text-slate-200 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-indigo-600 text-white font-medium rounded hover:bg-indigo-500 transition"
                >
                  Save SLO Definition
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
