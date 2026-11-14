"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Layers,
  Activity,
  AlertTriangle,
  Clock,
  ArrowRight,
  Filter,
  CheckCircle,
  XCircle,
  RefreshCw,
  GitCommit,
} from "lucide-react";

import { api } from "@/lib/api/client";
import { ServiceDependencyGraphResponse, ServiceDependencyNode } from "@/lib/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";

export default function ServiceDependenciesPage() {
  const [graph, setGraph] = useState<ServiceDependencyGraphResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeWindow, setTimeWindow] = useState(24);
  const [environment, setEnvironment] = useState("production");
  const [selectedService, setSelectedService] = useState<string | null>(null);

  const loadGraph = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getServiceDependencies({
        time_window_hours: timeWindow,
        environment: environment,
      });
      setGraph(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load service dependencies");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [timeWindow, environment]);

  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];

  // Filter edges based on selected service
  const filteredEdges = selectedService
    ? edges.filter(
        (e) => e.source_service === selectedService || e.target_service === selectedService
      )
    : edges;

  return (
    <AppShell>
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
                <Layers className="w-5 h-5" />
              </span>
              <h1 className="text-2xl font-bold tracking-tight text-slate-100">
                Service Dependency Map
              </h1>
              <span className="text-xs font-mono uppercase bg-cyan-950 text-cyan-400 border border-cyan-800/50 px-2 py-0.5 rounded">
                Live Topology
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Topological service graph derived directly from distributed trace parent-child span boundaries.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/traces"
              className="inline-flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 transition"
            >
              <GitCommit className="w-3.5 h-3.5 text-cyan-400" />
              Trace Explorer
            </Link>
          </div>
        </div>

        {/* Filter Controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-slate-900/50 rounded-xl border border-slate-800 text-xs">
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 text-slate-400">
              <Filter className="w-3.5 h-3.5 text-cyan-400" />
              <span>Time Window:</span>
            </div>

            <select
              value={timeWindow}
              onChange={(e) => setTimeWindow(Number(e.target.value))}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200"
            >
              <option value={6}>Last 6 Hours</option>
              <option value={24}>Last 24 Hours</option>
              <option value={72}>Last 3 Days</option>
            </select>

            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-slate-200"
            >
              <option value="production">Production</option>
              <option value="staging">Staging</option>
              <option value="demo">Demo</option>
            </select>
          </div>

          <button
            onClick={loadGraph}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-400" />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="py-12">
            <LoadingSkeleton count={5} />
          </div>
        ) : error ? (
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        ) : (
          <div className="space-y-6">
            {/* Service Nodes Grid */}
            <div className="space-y-3">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                <span>Discovered Service Nodes ({nodes.length})</span>
                {selectedService && (
                  <button
                    onClick={() => setSelectedService(null)}
                    className="text-cyan-400 hover:text-cyan-300 underline font-normal"
                  >
                    Clear selection ({selectedService})
                  </button>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {nodes.map((node: ServiceDependencyNode) => {
                  const isSelected = selectedService === node.service;
                  const isHealthy = node.health_status === "HEALTHY";
                  const isDegraded = node.health_status === "DEGRADED";
                  const isFailed = node.health_status === "FAILED";

                  return (
                    <div
                      key={node.service}
                      onClick={() =>
                        setSelectedService(isSelected ? null : node.service)
                      }
                      className={`p-4 rounded-xl border cursor-pointer transition-all ${
                        isSelected
                          ? "bg-slate-900 border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.2)]"
                          : "bg-slate-950 border-slate-800 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-sm text-slate-100 font-mono truncate">
                          {node.service}
                        </span>
                        {isHealthy && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
                            <CheckCircle className="w-3.5 h-3.5" /> Healthy
                          </span>
                        )}
                        {isDegraded && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-amber-400 font-medium">
                            <AlertTriangle className="w-3.5 h-3.5" /> Degraded
                          </span>
                        )}
                        {isFailed && (
                          <span className="inline-flex items-center gap-1 text-[11px] text-rose-400 font-medium">
                            <XCircle className="w-3.5 h-3.5" /> Failed
                          </span>
                        )}
                      </div>

                      <div className="grid grid-cols-2 gap-2 mt-4 text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 font-mono">REQUESTS</div>
                          <div className="font-mono text-slate-200 font-semibold">{node.request_count}</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 font-mono">ERROR RATE</div>
                          <div
                            className={`font-mono font-semibold ${
                              node.error_rate > 0.05 ? "text-rose-400" : "text-slate-300"
                            }`}
                          >
                            {(node.error_rate * 100).toFixed(1)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 font-mono">p95 LATENCY</div>
                          <div
                            className={`font-mono font-semibold ${
                              node.p95_latency_ms > 1000
                                ? "text-rose-400"
                                : node.p95_latency_ms > 500
                                ? "text-amber-400"
                                : "text-emerald-400"
                            }`}
                          >
                            {node.p95_latency_ms} ms
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 font-mono">ERRORS</div>
                          <div className="font-mono text-slate-200">{node.error_count}</div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Caller -> Callee Edges Table */}
            <div className="border border-slate-800 rounded-xl bg-slate-950 overflow-hidden shadow-sm">
              <div className="p-4 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                  Directed Service Invocations ({filteredEdges.length})
                </div>
                <div className="text-xs text-slate-500 font-mono">
                  Caller → Callee Relationships
                </div>
              </div>

              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 font-medium">
                    <th className="py-2.5 px-4">Caller (Upstream)</th>
                    <th className="py-2.5 px-4 text-center">Direction</th>
                    <th className="py-2.5 px-4">Callee (Downstream)</th>
                    <th className="py-2.5 px-4">Request Volume</th>
                    <th className="py-2.5 px-4">Error Rate</th>
                    <th className="py-2.5 px-4">p50 Latency</th>
                    <th className="py-2.5 px-4">p95 Latency</th>
                    <th className="py-2.5 px-4">p99 Latency</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {filteredEdges.map((edge, idx) => {
                    const isError = edge.error_rate > 0.05;
                    return (
                      <tr key={idx} className="hover:bg-slate-900/40 transition">
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
                            {edge.source_service}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-center text-slate-500">
                          <ArrowRight className="w-4 h-4 mx-auto text-cyan-400" />
                        </td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
                            {edge.target_service}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-300">{edge.request_count}</td>
                        <td className="py-2.5 px-4">
                          <span className={isError ? "text-rose-400 font-bold" : "text-slate-400"}>
                            {(edge.error_rate * 100).toFixed(1)}% ({edge.error_count})
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-400">{edge.p50_latency_ms} ms</td>
                        <td
                          className={`py-2.5 px-4 font-semibold ${
                            edge.p95_latency_ms > 1000
                              ? "text-rose-400"
                              : edge.p95_latency_ms > 500
                              ? "text-amber-400"
                              : "text-slate-300"
                          }`}
                        >
                          {edge.p95_latency_ms} ms
                        </td>
                        <td className="py-2.5 px-4 text-slate-400">{edge.p99_latency_ms} ms</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
