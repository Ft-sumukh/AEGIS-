"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  GitCommit,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ChevronRight,
  Layers,
  Sparkles,
  ArrowLeft,
  Copy,
  Check,
  Zap,
  Info,
} from "lucide-react";

import { api } from "@/lib/api/client";
import { TraceSpanNode, TraceTreeResponse } from "@/lib/api/types";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSkeleton } from "@/components/ui/LoadingSkeleton";

export default function TraceDetailPage() {
  const params = useParams();
  const traceId = params?.traceId as string;

  const [trace, setTrace] = useState<TraceTreeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<TraceSpanNode | null>(null);
  const [highlightCriticalPath, setHighlightCriticalPath] = useState(true);
  const [activeTab, setActiveTab] = useState<"waterfall" | "critical_path" | "error_propagation">("waterfall");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!traceId) return;
    const fetchTrace = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.getTrace(traceId);
        setTrace(data);
        if (data.root_span) {
          setSelectedSpan(data.root_span);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load trace");
      } finally {
        setLoading(false);
      }
    };
    fetchTrace();
  }, [traceId]);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(traceId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Flatten spans for waterfall view with depth indent
  const flattenSpans = (node: TraceSpanNode, depth: number = 0): Array<{ node: TraceSpanNode; depth: number }> => {
    let list: Array<{ node: TraceSpanNode; depth: number }> = [{ node, depth }];
    for (const child of node.children || []) {
      list = list.concat(flattenSpans(child, depth + 1));
    }
    return list;
  };

  const flattened = trace?.root_span ? flattenSpans(trace.root_span) : [];
  const criticalSpanIds = new Set(
    trace?.critical_path?.segments?.map((s) => s.span_id) || []
  );

  const getServiceColor = (service: string) => {
    switch (service) {
      case "api-gateway":
        return "bg-cyan-950 text-cyan-400 border-cyan-800/80";
      case "checkout-service":
        return "bg-blue-950 text-blue-400 border-blue-800/80";
      case "order-service":
        return "bg-indigo-950 text-indigo-400 border-indigo-800/80";
      case "payment-service":
        return "bg-rose-950 text-rose-400 border-rose-800/80";
      case "inventory-service":
        return "bg-emerald-950 text-emerald-400 border-emerald-800/80";
      case "postgres-cluster":
        return "bg-amber-950 text-amber-400 border-amber-800/80";
      case "reporting-worker":
        return "bg-purple-950 text-purple-400 border-purple-800/80";
      default:
        return "bg-slate-900 text-slate-300 border-slate-700";
    }
  };

  return (
    <AppShell>
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Navigation & Header */}
        <div className="flex flex-col gap-3 border-b border-slate-800 pb-5">
          <Link
            href="/traces"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-cyan-400 transition w-fit"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Traces</span>
          </Link>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="p-2 rounded-lg bg-cyan-950/80 border border-cyan-800/60 text-cyan-400">
                  <GitCommit className="w-5 h-5" />
                </span>
                <h1 className="text-xl font-bold tracking-tight text-slate-100 font-mono flex items-center gap-2">
                  <span>{traceId}</span>
                  <button
                    onClick={copyToClipboard}
                    className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                    title="Copy Trace ID"
                  >
                    {copied ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </h1>
              </div>

              {trace && (
                <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-slate-400">
                  <span>Root: <strong className="text-slate-200">{trace.root_span?.service_name}</strong></span>
                  <span>•</span>
                  <span>Duration: <strong className="text-slate-200">{trace.total_duration_ms} ms</strong></span>
                  <span>•</span>
                  <span>Spans: <strong className="text-slate-200">{trace.spans_count}</strong></span>
                  <span>•</span>
                  <span>Services: <strong className="text-slate-200">{trace.services.join(", ")}</strong></span>
                </div>
              )}
            </div>

            {trace && (
              <div className="flex items-center gap-2">
                {trace.status === "ERROR" || trace.error_count > 0 ? (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-300 border border-rose-800">
                    <XCircle className="w-4 h-4 text-rose-400" />
                    ERROR ({trace.error_count} failed spans)
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                    <CheckCircle className="w-4 h-4 text-emerald-400" />
                    STATUS OK
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

        {loading ? (
          <div className="py-12">
            <LoadingSkeleton count={6} />
          </div>
        ) : error || !trace ? (
          <div className="p-4 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs">
            {error || "Trace not found"}
          </div>
        ) : (
          <div className="space-y-6">
            {/* View Tabs & Critical Path Toggle */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/60 p-2 rounded-xl border border-slate-800 text-xs">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab("waterfall")}
                  className={`px-3 py-1.5 rounded-lg font-medium transition ${
                    activeTab === "waterfall"
                      ? "bg-slate-800 text-cyan-400 shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Waterfall Timeline ({flattened.length} spans)
                </button>
                <button
                  onClick={() => setActiveTab("critical_path")}
                  className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                    activeTab === "critical_path"
                      ? "bg-slate-800 text-amber-400 shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  Critical Path Analysis
                </button>
                {trace.error_propagation?.has_errors && (
                  <button
                    onClick={() => setActiveTab("error_propagation")}
                    className={`px-3 py-1.5 rounded-lg font-medium transition flex items-center gap-1.5 ${
                      activeTab === "error_propagation"
                        ? "bg-slate-800 text-rose-400 shadow-sm"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Error Propagation
                  </button>
                )}
              </div>

              {activeTab === "waterfall" && (
                <label className="flex items-center gap-2 cursor-pointer text-slate-300 select-none pr-2">
                  <input
                    type="checkbox"
                    checked={highlightCriticalPath}
                    onChange={(e) => setHighlightCriticalPath(e.target.checked)}
                    className="rounded border-slate-700 text-cyan-500 focus:ring-cyan-500 bg-slate-800"
                  />
                  <span>Highlight Critical Path</span>
                </label>
              )}
            </div>

            {/* TAB 1: WATERFALL TIMELINE & SPAN INSPECTOR */}
            {activeTab === "waterfall" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Waterfall Gantt Chart */}
                <div className="lg:col-span-2 border border-slate-800 rounded-xl bg-slate-950 p-4 space-y-3 overflow-x-auto shadow-sm">
                  <div className="flex items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-800/80">
                    <span className="font-semibold uppercase tracking-wider text-[10px]">
                      Operation Hierarchy
                    </span>
                    <span className="font-mono text-[10px]">
                      Timeline (0ms - {trace.total_duration_ms}ms)
                    </span>
                  </div>

                  <div className="space-y-1.5 pt-1">
                    {flattened.map(({ node, depth }) => {
                      const isSelected = selectedSpan?.span_id === node.span_id;
                      const isCritical = criticalSpanIds.has(node.span_id) && highlightCriticalPath;
                      const isError = node.status === "ERROR" || (node.http_status_code && node.http_status_code >= 500);

                      // Calculate Gantt bar offset & width percentages
                      const offsetPct = (node.start_offset_ms / Math.max(1, trace.total_duration_ms)) * 100;
                      const widthPct = Math.max(1.5, (node.duration_ms / Math.max(1, trace.total_duration_ms)) * 100);

                      return (
                        <div
                          key={node.span_id}
                          onClick={() => setSelectedSpan(node)}
                          className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                            isSelected
                              ? "bg-slate-900 border-cyan-500/80 shadow-[0_0_12px_rgba(6,182,212,0.15)]"
                              : isCritical
                              ? "bg-slate-900/40 border-amber-500/40 hover:border-amber-400/80"
                              : "bg-slate-900/20 border-slate-800/80 hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 text-xs mb-1.5">
                            <div className="flex items-center gap-2 truncate" style={{ paddingLeft: `${depth * 16}px` }}>
                              {depth > 0 && <ChevronRight className="w-3 h-3 text-slate-500 shrink-0" />}
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${getServiceColor(
                                  node.service_name
                                )}`}
                              >
                                {node.service_name}
                              </span>
                              <span className="font-medium text-slate-200 truncate">{node.operation_name}</span>
                            </div>

                            <div className="flex items-center gap-2 shrink-0 font-mono text-[11px]">
                              {isCritical && (
                                <span className="px-1.5 py-0.2 rounded bg-amber-950/80 text-amber-300 border border-amber-800/60 text-[10px]">
                                  Critical
                                </span>
                              )}
                              {isError ? (
                                <span className="text-rose-400 font-bold">ERR</span>
                              ) : null}
                              <span className="text-slate-400">{node.duration_ms} ms</span>
                            </div>
                          </div>

                          {/* Gantt Bar */}
                          <div className="w-full h-2 bg-slate-900 rounded-full overflow-hidden relative">
                            <div
                              className={`h-full rounded-full transition-all ${
                                isError
                                  ? "bg-rose-500"
                                  : isCritical
                                  ? "bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.4)]"
                                  : "bg-cyan-500"
                              }`}
                              style={{
                                marginLeft: `${offsetPct}%`,
                                width: `${widthPct}%`,
                              }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Span Details Drawer / Inspector */}
                <div className="border border-slate-800 rounded-xl bg-slate-950 p-4 space-y-4 shadow-sm h-fit">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <div className="font-semibold text-xs text-slate-200 flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-cyan-400" />
                      <span>Span Attributes Inspector</span>
                    </div>
                    {selectedSpan && (
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-mono border ${getServiceColor(
                          selectedSpan.service_name
                        )}`}
                      >
                        {selectedSpan.service_name}
                      </span>
                    )}
                  </div>

                  {selectedSpan ? (
                    <div className="space-y-3 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Operation</div>
                        <div className="font-medium text-slate-200 mt-0.5">{selectedSpan.operation_name}</div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Duration</div>
                          <div className="font-mono text-cyan-400 font-semibold mt-0.5">{selectedSpan.duration_ms} ms</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Self-Time</div>
                          <div className="font-mono text-slate-300 mt-0.5">{selectedSpan.self_time_ms} ms</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Status</div>
                          <div className="mt-0.5">
                            {selectedSpan.status === "ERROR" ? (
                              <span className="text-rose-400 font-semibold flex items-center gap-1">
                                <XCircle className="w-3.5 h-3.5" /> ERROR
                              </span>
                            ) : (
                              <span className="text-emerald-400 font-semibold flex items-center gap-1">
                                <CheckCircle className="w-3.5 h-3.5" /> OK
                              </span>
                            )}
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Span Kind</div>
                          <div className="font-mono text-slate-300 mt-0.5">{selectedSpan.span_kind}</div>
                        </div>
                      </div>

                      {selectedSpan.http_status_code && (
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">HTTP Status</div>
                          <div className="font-mono text-slate-200 mt-0.5">
                            {selectedSpan.http_method || "HTTP"} {selectedSpan.http_route || ""} →{" "}
                            <strong className={selectedSpan.http_status_code >= 500 ? "text-rose-400" : "text-emerald-400"}>
                              {selectedSpan.http_status_code}
                            </strong>
                          </div>
                        </div>
                      )}

                      {selectedSpan.status_message && (
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Error Message</div>
                          <div className="p-2 rounded bg-rose-950/40 border border-rose-900/60 text-rose-300 text-[11px] font-mono mt-0.5">
                            {selectedSpan.status_message}
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Span ID</div>
                        <div className="font-mono text-[11px] text-slate-400 mt-0.5 truncate">{selectedSpan.span_id}</div>
                      </div>

                      {selectedSpan.parent_span_id && (
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Parent Span ID</div>
                          <div className="font-mono text-[11px] text-slate-400 mt-0.5 truncate">{selectedSpan.parent_span_id}</div>
                        </div>
                      )}

                      {/* Sanitized Attributes */}
                      <div className="pt-2 border-t border-slate-800">
                        <div className="text-[10px] text-slate-400 uppercase tracking-wider font-mono mb-2 flex items-center justify-between">
                          <span>Sanitized Attributes (Group 7)</span>
                          <span className="text-emerald-400 text-[10px] font-normal">PII Redacted</span>
                        </div>
                        <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800/80 space-y-1.5 max-h-48 overflow-y-auto font-mono text-[11px]">
                          {Object.entries(selectedSpan.sanitized_attributes || {}).length === 0 ? (
                            <div className="text-slate-500 italic">No extra attributes</div>
                          ) : (
                            Object.entries(selectedSpan.sanitized_attributes).map(([k, v]) => (
                              <div key={k} className="flex items-start justify-between gap-2 border-b border-slate-800/40 pb-1">
                                <span className="text-slate-400">{k}:</span>
                                <span className="text-slate-200 text-right truncate max-w-[140px]">{String(v)}</span>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-6 text-slate-500 text-xs">
                      Click any span in the waterfall to inspect details
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: CRITICAL PATH BREAKDOWN */}
            {activeTab === "critical_path" && trace.critical_path && (
              <div className="border border-slate-800 rounded-xl bg-slate-950 p-6 space-y-5 shadow-sm">
                <div className="flex items-center gap-2 text-amber-400">
                  <Sparkles className="w-5 h-5" />
                  <h2 className="text-base font-semibold text-slate-100">
                    Latency Critical Path Analysis
                  </h2>
                </div>

                <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-800/50 text-amber-200 text-xs leading-relaxed flex items-start gap-2.5">
                  <Info className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-0.5">Non-Causal Latency Observation:</strong>
                    <span>{trace.critical_path.non_causal_assessment}</span>
                  </div>
                </div>

                <div className="border border-slate-800 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400">
                        <th className="py-2.5 px-3">Service</th>
                        <th className="py-2.5 px-3">Operation</th>
                        <th className="py-2.5 px-3">Total Duration</th>
                        <th className="py-2.5 px-3">Self-Time</th>
                        <th className="py-2.5 px-3">Critical Path Contribution</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {trace.critical_path.segments.map((seg) => (
                        <tr key={seg.span_id} className="hover:bg-slate-900/30">
                          <td className="py-2.5 px-3">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] border ${getServiceColor(seg.service_name)}`}>
                              {seg.service_name}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-slate-200">{seg.operation_name}</td>
                          <td className="py-2.5 px-3 text-slate-400">{seg.duration_ms} ms</td>
                          <td className="py-2.5 px-3 font-semibold text-cyan-400">{seg.self_time_ms} ms</td>
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              <span className="text-amber-400 font-bold">{seg.contribution_percent}%</span>
                              <div className="w-20 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                                <div
                                  className="h-full bg-amber-400"
                                  style={{ width: `${seg.contribution_percent}%` }}
                                />
                              </div>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* TAB 3: ERROR PROPAGATION */}
            {activeTab === "error_propagation" && trace.error_propagation && (
              <div className="border border-slate-800 rounded-xl bg-slate-950 p-6 space-y-5 shadow-sm">
                <div className="flex items-center gap-2 text-rose-400">
                  <AlertTriangle className="w-5 h-5" />
                  <h2 className="text-base font-semibold text-slate-100">
                    Downstream Error Propagation Chain
                  </h2>
                </div>

                <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-800/50 text-rose-200 text-xs leading-relaxed flex items-start gap-2.5">
                  <Info className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-0.5">Observed Error Sequence:</strong>
                    <span>{trace.error_propagation.non_causal_assessment}</span>
                  </div>
                </div>

                <div className="space-y-3 pt-2">
                  {trace.error_propagation.propagation_chain.map((step, idx) => (
                    <div
                      key={step.span_id}
                      className="p-3.5 rounded-xl border border-rose-900/40 bg-rose-950/10 flex items-center justify-between gap-4 text-xs font-mono"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-6 h-6 rounded-full bg-rose-950 border border-rose-800 text-rose-300 flex items-center justify-center text-[11px] font-bold">
                          {idx + 1}
                        </span>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className={`px-1.5 py-0.5 rounded text-[10px] border ${getServiceColor(step.service_name)}`}>
                              {step.service_name}
                            </span>
                            <span className="text-slate-200 font-semibold">{step.operation_name}</span>
                            {step.is_deepest_error && (
                              <span className="px-1.5 py-0.2 rounded bg-rose-900 text-rose-200 text-[10px] font-sans font-medium">
                                Downstream Failure Source
                              </span>
                            )}
                          </div>
                          {step.error_message && (
                            <div className="text-slate-400 text-[11px] mt-1 font-sans">
                              {step.error_message}
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-xs font-bold">
                          HTTP {step.http_status_code || step.status}
                        </span>
                        <div className="text-[10px] text-slate-500 mt-0.5">
                          {new Date(step.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </AppShell>
  );
}
