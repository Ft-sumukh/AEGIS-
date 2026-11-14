"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldCheck,
  Search,
  Filter,
  Lock,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Clock,
  User,
  Activity,
  Layers,
  FileCode,
  Shield,
  ChevronLeft,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { AuditEvent } from "@/lib/api/types";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [actionFilter, setActionFilter] = useState<string>("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState<string>("");
  const [actorIdFilter, setActorIdFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const limit = 20;

  // Expanded JSON metadata rows
  const [expandedRow, setExpandedRow] = useState<string | null>(null);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAuditLogs({
        action: actionFilter || undefined,
        resource_type: resourceTypeFilter || undefined,
        actor_id: actorIdFilter || undefined,
        limit,
        offset: page * limit,
      });
      setLogs(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit trail");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [actionFilter, resourceTypeFilter, actorIdFilter, page]);

  // Client-side text filtering for quick search
  const filteredLogs = logs.filter((log) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      log.actor_id.toLowerCase().includes(q) ||
      log.resource_type.toLowerCase().includes(q) ||
      (log.resource_id && log.resource_id.toLowerCase().includes(q)) ||
      (log.request_id && log.request_id.toLowerCase().includes(q))
    );
  });

  const toggleRow = (id: string) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-emerald-400 mb-1">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>IMMUTABLE SECURITY & COMPLIANCE LOG</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Audit Trail
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Tamper-evident log of all operator actions, automated anomaly correlations, and AI diagnostic tool runs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAuditLogs}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs font-mono text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <div className="text-xs font-mono text-slate-400">
            Showing <strong className="text-slate-200">{filteredLogs.length}</strong> of{" "}
            <strong className="text-slate-200">{total}</strong> records
          </div>
        </div>
      </div>

      {/* Governance & Privacy Notice */}
      <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-4 text-emerald-300 flex items-start gap-3">
        <Shield className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <div className="font-semibold font-mono tracking-wide text-emerald-200">
            CONTROLLED PRIVACY & SANITIZATION ACTIVE (GROUP 7)
          </div>
          <p className="text-emerald-300/80 leading-relaxed">
            All audit metadata is protected by Aegis Data-Governance rules. Sensitive credentials,
            customer emails, and payment identifiers are automatically redacted or pseudonymized before
            persisting and displaying.
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 backdrop-blur flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Search Input */}
        <div className="w-full md:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search action, actor, resource, trace ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:border-emerald-500/50"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Action:</span>
            <input
              type="text"
              placeholder="e.g. acknowledge"
              value={actionFilter}
              onChange={(e) => {
                setActionFilter(e.target.value);
                setPage(0);
              }}
              className="w-32 bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Resource:</span>
            <input
              type="text"
              placeholder="e.g. incident"
              value={resourceTypeFilter}
              onChange={(e) => {
                setResourceTypeFilter(e.target.value);
                setPage(0);
              }}
              className="w-28 bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 focus:outline-none focus:border-emerald-500"
            />
          </div>

          {(actionFilter || resourceTypeFilter || searchQuery) && (
            <button
              onClick={() => {
                setActionFilter("");
                setResourceTypeFilter("");
                setActorIdFilter("");
                setSearchQuery("");
                setPage(0);
              }}
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2 ml-1"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Audit Table */}
      {loading ? (
        <TableSkeleton rows={10} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchAuditLogs} />
      ) : filteredLogs.length === 0 ? (
        <EmptyState
          title="No audit events found"
          description="There are no audit events matching your filter criteria."
          actionLabel="Reset Filters"
          onAction={() => {
            setActionFilter("");
            setResourceTypeFilter("");
            setActorIdFilter("");
            setSearchQuery("");
            setPage(0);
          }}
        />
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-900/40 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-slate-400">
                  <th className="py-3 px-4 w-8"></th>
                  <th className="py-3 px-4 font-medium">Timestamp</th>
                  <th className="py-3 px-4 font-medium">Actor</th>
                  <th className="py-3 px-4 font-medium">Action</th>
                  <th className="py-3 px-4 font-medium">Resource</th>
                  <th className="py-3 px-4 font-medium">Request ID</th>
                  <th className="py-3 px-4 font-medium text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredLogs.map((log) => {
                  const isExpanded = expandedRow === log.id;
                  const hasMetadata =
                    log.audit_metadata && Object.keys(log.audit_metadata).length > 0;

                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => hasMetadata && toggleRow(log.id)}
                        className={`hover:bg-slate-850/50 transition-colors ${
                          hasMetadata ? "cursor-pointer" : ""
                        } ${isExpanded ? "bg-slate-850/40" : ""}`}
                      >
                        <td className="py-3 px-4 text-slate-500">
                          {hasMetadata ? (
                            isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
                            )
                          ) : null}
                        </td>
                        <td className="py-3 px-4 text-slate-300 whitespace-nowrap">
                          <div className="flex items-center gap-1.5 text-slate-400">
                            <Clock className="w-3 h-3 text-slate-500" />
                            <span>{new Date(log.timestamp).toLocaleString()}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center gap-1.5">
                            <User className="w-3 h-3 text-cyan-400" />
                            <span className="text-cyan-300 font-semibold">{log.actor_id}</span>
                            <span className="text-[10px] text-slate-500">({log.actor_type})</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-200 font-semibold">
                            {log.action}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-300">
                          <div className="flex items-center gap-1.5">
                            <span className="text-purple-400">{log.resource_type}</span>
                            {log.resource_id && (
                              <span className="text-slate-500 font-mono text-[11px] truncate max-w-[120px]">
                                :{log.resource_id}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                          {log.request_id ? (
                            <span title={log.request_id} className="truncate max-w-[100px] block">
                              {log.request_id.slice(0, 8)}...
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="py-3 px-4 text-right">
                          {hasMetadata ? (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                toggleRow(log.id);
                              }}
                              className="text-[11px] text-emerald-400 hover:text-emerald-300 underline"
                            >
                              {isExpanded ? "Hide" : "Inspect"}
                            </button>
                          ) : (
                            <span className="text-slate-600 text-[11px]">None</span>
                          )}
                        </td>
                      </tr>

                      {/* Expanded Details / Sanitized Metadata */}
                      {isExpanded && (
                        <tr className="bg-slate-950/80">
                          <td colSpan={7} className="py-3 px-6 border-b border-slate-800">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between text-[11px] text-slate-400">
                                <span className="font-semibold text-emerald-400 flex items-center gap-1">
                                  <Lock className="w-3 h-3" /> Sanitized Event Metadata (Redacted & Pseudonymized)
                                </span>
                                <span>Event ID: {log.id}</span>
                              </div>
                              <pre className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] text-emerald-300/90 font-mono overflow-x-auto">
                                {JSON.stringify(log.audit_metadata, null, 2)}
                              </pre>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800 p-4 bg-slate-950/40">
            <div className="text-xs font-mono text-slate-500">
              Page <span className="text-slate-300">{page + 1}</span> of{" "}
              <span className="text-slate-300">{Math.ceil(total / limit) || 1}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="flex items-center gap-1 px-3 py-1 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * limit >= total}
                className="flex items-center gap-1 px-3 py-1 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
