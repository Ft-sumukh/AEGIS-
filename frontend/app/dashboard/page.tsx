"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  Cpu,
  Layers,
  Sparkles,
  TrendingDown,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { OverviewData } from "@/lib/api/types";
import { KpiCard } from "@/components/ui/KpiCard";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { BoundaryBadge } from "@/components/ui/BoundaryBadge";
import { CardSkeleton, ChartSkeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { MetricChart } from "@/components/charts/MetricChart";

export default function DashboardPage() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getOverview();
      setData(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load operations overview");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading && !data) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-64 bg-slate-800 rounded animate-pulse" />
        <CardSkeleton count={4} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <ChartSkeleton />
          </div>
          <div>
            <ChartSkeleton />
          </div>
        </div>
        <TableSkeleton rows={4} cols={5} />
      </div>
    );
  }

  if (error && !data) {
    return <ErrorState message={error} onRetry={fetchDashboardData} />;
  }

  if (!data) return null;

  const kpis = data.kpis;
  const criticalIncident = data.recent_incidents.find((i) => i.severity === "CRITICAL");
  const leadingHypothesis = data.latest_investigation?.hypotheses.find(
    (h) => h.status === "SUPPORTED"
  );

  // Synthetic charts telemetry points
  const checkoutData = [
    { timestamp: "13:45", timeLabel: "13:45", value: 0.02, baseline: 0.02 },
    { timestamp: "13:50", timeLabel: "13:50", value: 0.02, baseline: 0.02 },
    { timestamp: "13:55", timeLabel: "13:55", value: 0.03, baseline: 0.02 },
    { timestamp: "14:00", timeLabel: "14:00", value: 0.02, baseline: 0.02, isDeployment: true, deploymentVersion: "v4.8.2" },
    { timestamp: "14:05", timeLabel: "14:05", value: 4.8, baseline: 0.02 },
    { timestamp: "14:07", timeLabel: "14:07", value: 24.5, baseline: 0.02 },
    { timestamp: "14:10", timeLabel: "14:10", value: 42.8, baseline: 0.02, isAnomaly: true },
    { timestamp: "14:15", timeLabel: "14:15", value: 41.2, baseline: 0.02 },
    { timestamp: "14:20", timeLabel: "14:20", value: 39.5, baseline: 0.02 },
  ];

  const apiErrorData = [
    { timestamp: "13:45", timeLabel: "13:45", value: 0.1, baseline: 0.1 },
    { timestamp: "13:50", timeLabel: "13:50", value: 0.12, baseline: 0.1 },
    { timestamp: "13:55", timeLabel: "13:55", value: 0.09, baseline: 0.1 },
    { timestamp: "14:00", timeLabel: "14:00", value: 0.11, baseline: 0.1, isDeployment: true },
    { timestamp: "14:05", timeLabel: "14:05", value: 8.2, baseline: 0.1 },
    { timestamp: "14:07", timeLabel: "14:07", value: 14.1, baseline: 0.1 },
    { timestamp: "14:10", timeLabel: "14:10", value: 18.5, baseline: 0.1, isAnomaly: true },
    { timestamp: "14:15", timeLabel: "14:15", value: 17.8, baseline: 0.1 },
    { timestamp: "14:20", timeLabel: "14:20", value: 16.9, baseline: 0.1 },
  ];

  return (
    <div className="space-y-8">
      {/* 1. Dashboard Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span>OPERATIONS INTELLIGENCE // LIVE OBSERVABILITY</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-bold font-mono tracking-tight text-white">
            Operations Console
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time telemetry, anomaly correlation clusters, and governed AI diagnostics for{" "}
            <span className="text-slate-200 font-semibold">{data.company_name}</span>.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/incidents"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium font-mono text-slate-200 bg-slate-900 border border-slate-800 hover:bg-slate-800 transition-colors"
          >
            <span>View All Incidents</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* 2. Critical Active Incident Alert Banner */}
      {criticalIncident && (
        <div className="rounded-xl border border-rose-800/80 bg-rose-950/20 p-5 backdrop-blur flex flex-col md:flex-row items-start md:items-center justify-between gap-4 animate-fadeIn">
          <div className="flex items-start gap-4">
            <div className="p-2.5 rounded-lg bg-rose-950/80 border border-rose-700 text-rose-400 shrink-0 mt-0.5">
              <AlertTriangle className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={criticalIncident.severity} size="sm" />
                <StatusBadge status={criticalIncident.status} size="sm" />
                <span className="text-xs font-mono text-rose-300">
                  {criticalIncident.category} • Detected at {new Date(criticalIncident.detected_at).toLocaleTimeString()}
                </span>
              </div>
              <h3 className="text-base font-bold text-white tracking-tight">
                {criticalIncident.title}
              </h3>
              <p className="text-xs text-slate-300 mt-1 line-clamp-2 max-w-3xl">
                {criticalIncident.summary}
              </p>
              <div className="flex flex-wrap items-center gap-4 mt-3 text-xs font-mono text-slate-400">
                <span>
                  Impact:{" "}
                  <strong className="text-rose-300">
                    ${criticalIncident.estimated_revenue_impact?.toLocaleString() || "12,500"}
                  </strong>
                </span>
                <span>
                  Orders Affected:{" "}
                  <strong className="text-white">
                    {criticalIncident.estimated_orders_affected || "148"}
                  </strong>
                </span>
                <span>
                  Systems:{" "}
                  <strong className="text-cyan-400">
                    {criticalIncident.affected_systems?.join(", ") || "checkout-service"}
                  </strong>
                </span>
              </div>
            </div>
          </div>

          <Link
            href={`/incidents/${criticalIncident.id}`}
            className="shrink-0 inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold font-mono text-white bg-rose-600 hover:bg-rose-500 shadow-[0_0_15px_rgba(225,29,72,0.3)] transition-all"
          >
            <span>Inspect Incident</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* 3. Global KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Active Incidents"
          value={kpis.active_incidents}
          status={kpis.critical_incidents > 0 ? "critical" : kpis.active_incidents > 0 ? "warning" : "healthy"}
          comparisonPeriod={`${kpis.critical_incidents} Critical (SEV-1)`}
          icon={AlertTriangle}
        />
        <KpiCard
          title="Est. Revenue Impact"
          value={`$${Math.round(kpis.estimated_revenue_impact).toLocaleString()}`}
          unit="USD"
          trend={kpis.estimated_revenue_impact > 0 ? 840 : 0}
          trendDirection="up"
          status={kpis.estimated_revenue_impact > 5000 ? "critical" : "normal"}
          comparisonPeriod="vs baseline window"
          icon={TrendingDown}
        />
        <KpiCard
          title="Checkout Failure Rate"
          value={`${kpis.checkout_failure_rate_current.toFixed(1)}%`}
          trend={kpis.checkout_failure_rate_current > 1.0 ? 2140 : 0}
          trendDirection="up"
          status={kpis.checkout_failure_rate_current > 5.0 ? "critical" : "normal"}
          comparisonPeriod="Baseline: 0.02%"
          icon={AlertTriangle}
        />
        <KpiCard
          title="Affected Systems"
          value={kpis.affected_systems_count}
          status={kpis.affected_systems_count > 1 ? "warning" : "normal"}
          comparisonPeriod="checkout-service, postgres"
          icon={Layers}
        />
      </div>

      {/* 4. Telemetry Time-Series Charts & AI Investigation Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metric Charts Column */}
        <div className="lg:col-span-2 space-y-6">
          <MetricChart
            title="Checkout Failure Rate"
            unit="%"
            data={checkoutData}
            incidentWindow={{ start: "14:05", end: "14:20", label: "Incident Window" }}
            deploymentTimestamp="14:00"
            deploymentLabel="v4.8.2 Deployed"
            color="#f43f5e"
            height={220}
          />
          <MetricChart
            title="API Gateway 5xx Error Rate"
            unit="%"
            data={apiErrorData}
            deploymentTimestamp="14:00"
            deploymentLabel="v4.8.2 Deployed"
            color="#06b6d4"
            height={180}
          />
        </div>

        {/* AI Investigation Summary Panel */}
        <div className="space-y-6">
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wider">
                  AI Investigation Summary
                </h3>
              </div>
              <BoundaryBadge type="ASSESSMENT" />
            </div>

            {data.latest_investigation ? (
              <div className="space-y-3.5">
                <div>
                  <div className="text-[11px] font-mono text-slate-400 uppercase">
                    Leading Hypothesis
                  </div>
                  <div className="text-sm font-semibold text-white mt-1">
                    {leadingHypothesis?.title || "Deployment v4.8.2 connection pool exhaustion"}
                  </div>
                  <p className="text-xs text-slate-300 mt-1 font-sans">
                    {leadingHypothesis?.description ||
                      "Unclosed connection leak in exception block of checkout service."}
                  </p>
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/60 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">Diagnostic Confidence</span>
                    <span className="text-emerald-400 font-bold">
                      {Math.round((data.latest_investigation.confidence || 0.91) * 100)}% High
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-emerald-400 rounded-full"
                      style={{
                        width: `${Math.round((data.latest_investigation.confidence || 0.91) * 100)}%`,
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 pt-1">
                    <span>Uncertainty: {Math.round((data.latest_investigation.uncertainty || 0.09) * 100)}%</span>
                    <span>Signals: 3 Verified Evidence</span>
                  </div>
                </div>

                {data.latest_investigation.recommendations.length > 0 && (
                  <div className="pt-2 border-t border-slate-800">
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[11px] font-mono text-slate-400 uppercase">
                        AI Recommendation
                      </span>
                      <BoundaryBadge type="RECOMMENDATION" />
                    </div>
                    <div className="text-xs font-medium text-amber-300">
                      {data.latest_investigation.recommendations[0].title}
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      Priority:{" "}
                      <strong className="text-rose-400">
                        {data.latest_investigation.recommendations[0].priority}
                      </strong>{" "}
                      • Risk: {data.latest_investigation.recommendations[0].risk_level}
                    </p>
                  </div>
                )}

                <Link
                  href={`/investigations/${data.latest_investigation.id}`}
                  className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-mono text-cyan-300 bg-cyan-950/40 border border-cyan-800/60 hover:bg-cyan-900/40 transition-colors"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Open Full Investigation</span>
                </Link>
              </div>
            ) : (
              <div className="p-6 text-center text-xs font-mono text-slate-500">
                No active investigation runs
              </div>
            )}
          </div>

          {/* System Health Snapshot */}
          <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-slate-400" />
                <h3 className="text-xs font-semibold font-mono text-slate-200 uppercase tracking-wider">
                  Core System Health
                </h3>
              </div>
              <Link href="/systems" className="text-xs font-mono text-cyan-400 hover:underline">
                All Systems →
              </Link>
            </div>

            <div className="space-y-2">
              {data.systems_summary.map((sys) => (
                <div
                  key={sys.name}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-slate-800/60 bg-slate-950/40 text-xs font-mono"
                >
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2 h-2 rounded-full ${
                        sys.status === "CRITICAL"
                          ? "bg-rose-500 animate-pulse"
                          : sys.status === "DEGRADED"
                          ? "bg-amber-500"
                          : "bg-emerald-400"
                      }`}
                    />
                    <span className="text-slate-200">{sys.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-slate-400">{sys.latency_ms}ms</span>
                    <StatusBadge status={sys.status} size="sm" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 5. Active Incidents Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden backdrop-blur">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div>
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Active Operational Incidents
            </h3>
            <p className="text-xs text-slate-400">
              Correlated operational incidents requiring active triage or remediation
            </p>
          </div>
          <Link
            href="/incidents"
            className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
          >
            <span>Incident Center</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Incident Title</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Affected Systems</th>
                <th className="py-3 px-4">Revenue Impact</th>
                <th className="py-3 px-4">AI Confidence</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {data.recent_incidents.map((inc) => (
                <tr key={inc.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 px-4">
                    <SeverityBadge severity={inc.severity} size="sm" />
                  </td>
                  <td className="py-3 px-4">
                    <div className="font-sans font-medium text-slate-200 text-xs">
                      {inc.title}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                      {inc.category} • Detected {new Date(inc.detected_at).toLocaleString()}
                    </div>
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={inc.status} size="sm" />
                  </td>
                  <td className="py-3 px-4 text-cyan-300">
                    {inc.affected_systems?.join(", ") || "—"}
                  </td>
                  <td className="py-3 px-4 text-rose-300 font-bold">
                    ${inc.estimated_revenue_impact?.toLocaleString() || "0"}
                  </td>
                  <td className="py-3 px-4 text-emerald-400">
                    {inc.confidence ? `${Math.round(inc.confidence * 100)}%` : "—"}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Link
                      href={`/incidents/${inc.id}`}
                      className="px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-cyan-400 hover:bg-slate-800 transition-colors"
                    >
                      Inspect →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
