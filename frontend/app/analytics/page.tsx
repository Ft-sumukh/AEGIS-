"use client";

import React, { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Calendar,
  Filter,
  Play,
  Radio,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { Anomaly, AnomalySummary, OperationalMetric } from "@/lib/api/types";
import { MetricChart, ChartDataPoint } from "@/components/charts/MetricChart";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ChartSkeleton, TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function AnalyticsPage() {
  const [selectedMetric, setSelectedMetric] = useState("checkout_failure_rate");
  const [metrics, setMetrics] = useState<OperationalMetric[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [summary, setSummary] = useState<AnomalySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggeringRun, setTriggeringRun] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [metricsRes, anomsRes, summaryRes] = await Promise.all([
        api.getMetrics({ metric_name: selectedMetric, limit: 100 }),
        api.getAnomalies({ limit: 50 }),
        api.getAnomalySummary(),
      ]);
      setMetrics(metricsRes.items);
      setAnomalies(anomsRes.items);
      setSummary(summaryRes);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load telemetry analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedMetric]);

  const handleRunAnalytics = async () => {
    try {
      setTriggeringRun(true);
      await api.triggerAnalyticsRun({ metric_filter: [selectedMetric] });
      setRunMessage("Analytics pipeline completed successfully. Refreshing anomaly clusters...");
      await fetchData();
    } catch (err: unknown) {
      setRunMessage(`Analytics run failed: ${err instanceof Error ? err.message : "Error"}`);
    } finally {
      setTriggeringRun(false);
    }
  };

  // Transform metrics & anomalies into ChartDataPoints
  const chartData: ChartDataPoint[] = metrics
    .slice()
    .reverse()
    .map((m) => {
      const ts = new Date(m.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      const anomMatch = anomalies.find(
        (a) => a.metric_name === m.metric_name && Math.abs(a.observed_value - m.value) < 0.01
      );
      return {
        timestamp: new Date(m.timestamp).toLocaleString(),
        timeLabel: ts,
        value: m.value,
        baseline: selectedMetric === "checkout_failure_rate" ? 0.02 : selectedMetric === "api_error_rate" ? 0.12 : undefined,
        isAnomaly: Boolean(anomMatch),
        anomalyDetails: anomMatch,
        isDeployment: ts.includes("14:00") || ts.includes("02:00"),
        deploymentVersion: "v4.8.2",
      };
    });

  const availableMetrics = [
    { id: "checkout_failure_rate", name: "Checkout Failure Rate", unit: "%" },
    { id: "api_error_rate", name: "API Gateway 5xx Rate", unit: "%" },
    { id: "revenue", name: "Order Revenue", unit: "USD/min" },
    { id: "active_users", name: "Active Users", unit: "users" },
  ];

  const currentMetricDef = availableMetrics.find((m) => m.id === selectedMetric) || availableMetrics[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Radio className="w-3.5 h-3.5" />
            <span>OPERATIONAL TELEMETRY & STATISTICAL ANOMALIES</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Telemetry Analytics
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Statistical deviation detectors, baseline models, and cross-metric correlation engines.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRunAnalytics}
            disabled={triggeringRun}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-mono font-bold text-cyan-300 bg-cyan-950/60 border border-cyan-800 hover:bg-cyan-900/50 disabled:opacity-50 transition-colors"
          >
            <Play className="w-3.5 h-3.5 text-cyan-400" />
            <span>{triggeringRun ? "Analyzing..." : "Trigger Analytics Run"}</span>
          </button>
        </div>
      </div>

      {runMessage && (
        <div className="p-3 rounded-lg border border-cyan-800 bg-cyan-950/40 text-xs font-mono text-cyan-200 flex items-center justify-between">
          <span>{runMessage}</span>
          <button onClick={() => setRunMessage(null)} className="text-slate-400 hover:text-white">
            ✕
          </button>
        </div>
      )}

      {/* Metric Selector & Filter Bar */}
      <div className="flex flex-wrap items-center gap-2 p-1.5 rounded-xl border border-slate-800 bg-slate-950/60 backdrop-blur">
        {availableMetrics.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelectedMetric(m.id)}
            className={`px-3 py-2 rounded-lg text-xs font-mono font-medium transition-all ${
              selectedMetric === m.id
                ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.1)]"
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900 border border-transparent"
            }`}
          >
            {m.name}
          </button>
        ))}
      </div>

      {/* Main Metric Chart */}
      {loading ? (
        <ChartSkeleton />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchData} />
      ) : (
        <MetricChart
          title={currentMetricDef.name}
          unit={currentMetricDef.unit}
          data={chartData}
          deploymentTimestamp="14:00"
          deploymentLabel="v4.8.2 Deployed"
          color={selectedMetric.includes("rate") ? "#f43f5e" : "#06b6d4"}
          height={320}
        />
      )}

      {/* Statistical Summary Tiles */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <div className="text-[10px] font-mono text-slate-400 uppercase">Total Detected Anomalies</div>
            <div className="text-2xl font-bold font-mono text-white mt-1">
              {summary.total_anomalies}
            </div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <div className="text-[10px] font-mono text-slate-400 uppercase">Critical Severity</div>
            <div className="text-2xl font-bold font-mono text-rose-400 mt-1">
              {summary.by_severity?.CRITICAL || 0}
            </div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <div className="text-[10px] font-mono text-slate-400 uppercase">Correlated Clusters</div>
            <div className="text-2xl font-bold font-mono text-purple-400 mt-1">
              {summary.by_status?.CORRELATED || 0}
            </div>
          </div>
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-950/60">
            <div className="text-[10px] font-mono text-slate-400 uppercase">Primary Detector</div>
            <div className="text-lg font-bold font-mono text-cyan-400 mt-1">
              Z-Score & Threshold
            </div>
          </div>
        </div>
      )}

      {/* Anomalies Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden backdrop-blur space-y-2">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div>
            <h3 className="text-sm font-semibold font-mono text-slate-200 uppercase tracking-wider">
              Detected Anomalies Index
            </h3>
            <p className="text-xs text-slate-400">
              Statistical deviations flagged by operational detectors
            </p>
          </div>
          <span className="text-xs font-mono text-slate-500">{anomalies.length} observations</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 text-[11px] uppercase tracking-wider">
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Metric</th>
                <th className="py-3 px-4">Detector</th>
                <th className="py-3 px-4">Observed vs Expected</th>
                <th className="py-3 px-4">Deviation</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4">Detected At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {anomalies.map((anom) => (
                <tr key={anom.id} className="hover:bg-slate-900/40 transition-colors">
                  <td className="py-3 px-4 whitespace-nowrap">
                    <SeverityBadge severity={anom.severity} size="sm" />
                  </td>
                  <td className="py-3 px-4 font-medium text-slate-200">{anom.metric_name}</td>
                  <td className="py-3 px-4 text-slate-400">{anom.detector_type}</td>
                  <td className="py-3 px-4 text-slate-300">
                    <span className="text-rose-400 font-bold">{anom.observed_value}</span>{" "}
                    <span className="text-slate-500">vs</span> {anom.expected_value ?? "—"}
                  </td>
                  <td className="py-3 px-4 text-rose-300 font-bold">
                    +{anom.deviation ?? "—"}
                  </td>
                  <td className="py-3 px-4 text-emerald-400">
                    {Math.round(anom.confidence * 100)}%
                  </td>
                  <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                    {new Date(anom.detected_at).toLocaleString()}
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
