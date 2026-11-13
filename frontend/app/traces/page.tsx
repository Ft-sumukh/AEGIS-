"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  GitCommit,
  Search,
  Filter,
  AlertTriangle,
  Clock,
  CheckCircle,
  XCircle,
  Layers,
  ArrowRight,
  Activity,
  Zap,
} from "lucide-react";

import { api } from "@/lib/api/client";
import { TraceSummaryItem } from "@/lib/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";
import { EmptyState } from "@/components/ui/EmptyState";

export default function TracesPage() {
  const [traces, setTraces] = useState<TraceSummaryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTraceId, setSearchTraceId] = useState("");
  const [selectedService, setSelectedService] = useState("");
  const [selectedStatus, setSelectedStatus] = useState("");
  const [minDuration, setMinDuration] = useState("");
  const [activeTab, setActiveTab] = useState<"all" | "slow" | "errors">("all");

  const loadTraces = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "slow") {
        const res = await api.getSlowTraces({
          min_duration_ms: 500,
          service: selectedService || undefined,
          limit: 50,
        });
        setTraces(res);
        setTotal(res.length);
      } else if (activeTab === "errors") {
        const res = await api.getErrorTraces({
          service: selectedService || undefined,
          limit: 50,
        });
        setTraces(res);
        setTotal(res.length);
      } else {
        const res = await api.listTraces({
          service: selectedService || undefined,
          status: selectedStatus || undefined,
          min_duration_ms: minDuration ? parseFloat(minDuration) : undefined,
          limit: 50,
        });
        setTraces(res.items || []);
        setTotal(res.total || 0);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load distributed traces";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTraces();
  }, [selectedService, selectedStatus, minDuration, activeTab]);

  // Derived KPIs
  const errorCount = traces.filter((t) => t.status === "ERROR").length;
  const avgDuration =
    traces.length > 0
      ? Math.round(traces.reduce((acc, t) => acc + t.duration_ms, 0) / traces.length)
      : 0;
  const p95Duration =
    traces.length > 0
      ? [...traces].sort((a, b) => a.duration_ms - b.duration_ms)[
          Math.floor(traces.length * 0.95)
        ]?.duration_ms || 0
      : 0;

  const filteredTraces = searchTraceId
    ? traces.filter((t) => t.trace_id.toLowerCase().includes(searchTraceId.toLowerCase().trim()))
    : traces;

  return (
    <AppShell>
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.2)]">
                <GitCommit className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Distributed Tracing
              </h1>
              <span className="text-xs font-mono uppercase bg-cyan-950 text-cyan-400 border border-cyan-800/50 px-2 py-0.5 rounded">
                OTel Standard
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              End-to-end request transaction traces, latency critical paths, and cross-service error propagation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/systems/dependencies"
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 transition"
            >
              <Layers className="w-3.5 h-3.5 text-cyan-400" />
              Service Dependency Map
            </Link>
          </div>
        </div>

        {/* Top Metric KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Total Traces</span>
              <Activity className="w-4 h-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-100 mt-2">{total}</div>
            <div className="text-[11px] text-slate-500 mt-1">Captured in active window</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Error Traces</span>
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-rose-400 mt-2">{errorCount}</div>
            <div className="text-[11px] text-slate-500 mt-1">
              {total > 0 ? `${((errorCount / total) * 100).toFixed(1)}% error rate` : "0% error rate"}
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Avg Latency</span>
              <Clock className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-100 mt-2">{avgDuration} ms</div>
            <div className="text-[11px] text-slate-500 mt-1">End-to-end execution</div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>p95 Latency</span>
              <Zap className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-purple-300 mt-2">{p95Duration} ms</div>
            <div className="text-[11px] text-slate-500 mt-1">95th percentile duration</div>
          </div>
        </div>

        {/* View Tabs & Search Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          {/* Tabs */}
          <div className="flex items-center bg-slate-900/80 p-1 rounded-lg border border-slate-800 text-xs font-medium">
            <button
              onClick={() => setActiveTab("all")}
              className={`px-3 py-1.5 rounded-md transition ${
                activeTab === "all"
                  ? "bg-slate-800 text-cyan-400 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              All Traces
            </button>
            <button
              onClick={() => setActiveTab("slow")}
              className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
                activeTab === "slow"
                  ? "bg-slate-800 text-amber-400 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              Slow Traces (&gt;500ms)
            </button>
            <button
              onClick={() => setActiveTab("errors")}
              className={`px-3 py-1.5 rounded-md transition flex items-center gap-1.5 ${
                activeTab === "errors"
                  ? "bg-slate-800 text-rose-400 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Errors & 5xx
            </button>
          </div>

          {/* Trace ID Search */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by Trace ID..."
              value={searchTraceId}
              onChange={(e) => setSearchTraceId(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/50 font-mono"
            />
          </div>
        </div>

        {/* Filters Bar */}
        <div className="flex flex-wrap items-center gap-3 p-3 bg-slate-900/40 rounded-xl border border-slate-800/80 text-xs">
          <div className="flex items-center gap-1.5 text-slate-400 mr-2">
            <Filter className="w-3.5 h-3.5 text-cyan-400" />
            <span>Filters:</span>
          </div>

          {/* Service Dropdown */}
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="">All Services</option>
            <option value="api-gateway">api-gateway</option>
            <option value="checkout-service">checkout-service</option>
            <option value="order-service">order-service</option>
            <option value="payment-service">payment-service</option>
            <option value="inventory-service">inventory-service</option>
            <option value="postgres-cluster">postgres-cluster</option>
            <option value="reporting-worker">reporting-worker</option>
          </select>

          {/* Status Dropdown */}
          {activeTab === "all" && (
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Statuses</option>
              <option value="OK">OK Only</option>
              <option value="ERROR">ERROR Only</option>
            </select>
          )}

          {/* Min Latency Dropdown */}
          {activeTab === "all" && (
            <select
              value={minDuration}
              onChange={(e) => setMinDuration(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">Any Latency</option>
              <option value="200">&gt; 200 ms</option>
              <option value="500">&gt; 500 ms</option>
              <option value="1000">&gt; 1,000 ms</option>
              <option value="2000">&gt; 2,000 ms</option>
            </select>
          )}

          {(selectedService || selectedStatus || minDuration || searchTraceId) && (
            <button
              onClick={() => {
                setSelectedService("");
                setSelectedStatus("");
                setMinDuration("");
                setSearchTraceId("");
              }}
              className="text-cyan-400 hover:text-cyan-300 underline ml-auto text-xs"
            >
              Reset filters
            </button>
          )}
        </div>

        {/* Traces Table */}
        {loading ? (
          <div className="py-12">
            <LoadingSkeleton count={6} />
          </div>
        ) : error ? (
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        ) : filteredTraces.length === 0 ? (
          <EmptyState
            title="No Distributed Traces Found"
            description="No traces matched the specified search criteria or time window."
          />
        ) : (
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-950 shadow-sm">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-medium">
                  <th className="py-3 px-4">Trace ID</th>
                  <th className="py-3 px-4">Root Service & Operation</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Services Involved</th>
                  <th className="py-3 px-4">Spans</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredTraces.map((trace) => {
                  const isErr = trace.status === "ERROR" || trace.error_count > 0;
                  return (
                    <tr
                      key={trace.trace_id}
                      className="hover:bg-slate-900/40 transition-colors group"
                    >
                      <td className="py-3 px-4 font-mono font-medium text-slate-200">
                        <Link
                          href={`/traces/${trace.trace_id}`}
                          className="hover:text-cyan-400 underline decoration-cyan-500/30 underline-offset-4"
                        >
                          {trace.trace_id.slice(0, 16)}...
                        </Link>
                      </td>

                      <td className="py-3 px-4">
                        <div className="font-medium text-slate-200">{trace.root_service}</div>
                        <div className="text-slate-500 font-mono text-[11px] truncate max-w-xs">
                          {trace.root_operation}
                        </div>
                      </td>

                      <td className="py-3 px-4">
                        {isErr ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-rose-950/80 text-rose-300 border border-rose-800/60">
                            <XCircle className="w-3 h-3 text-rose-400" />
                            ERROR ({trace.error_count})
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                            <CheckCircle className="w-3 h-3 text-emerald-400" />
                            OK
                          </span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-xs">
                          {trace.services.map((svc) => (
                            <span
                              key={svc}
                              className="px-1.5 py-0.5 rounded bg-slate-900 text-[10px] text-slate-300 border border-slate-800 font-mono"
                            >
                              {svc}
                            </span>
                          ))}
                        </div>
                      </td>

                      <td className="py-3 px-4 font-mono text-slate-300">
                        {trace.span_count}
                      </td>

                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`font-mono font-semibold ${
                              trace.duration_ms > 1500
                                ? "text-rose-400"
                                : trace.duration_ms > 500
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {trace.duration_ms} ms
                          </span>
                          <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden hidden sm:block">
                            <div
                              className={`h-full ${
                                trace.duration_ms > 1500
                                  ? "bg-rose-500"
                                  : trace.duration_ms > 500
                                  ? "bg-amber-500"
                                  : "bg-emerald-500"
                              }`}
                              style={{
                                width: `${Math.min(100, (trace.duration_ms / 3000) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>

                      <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                        {new Date(trace.timestamp_start).toLocaleTimeString()}
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/traces/${trace.trace_id}`}
                          className="inline-flex items-center gap-1 text-slate-400 hover:text-cyan-400 transition"
                        >
                          <span>Inspect</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
