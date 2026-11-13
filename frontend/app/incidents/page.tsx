"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Search, Filter, AlertTriangle, ArrowUpDown } from "lucide-react";
import { api } from "@/lib/api/client";
import { Incident, PaginatedResponse } from "@/lib/api/types";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(0);
  const limit = 20;

  const fetchIncidents = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getIncidents({
        search: search.trim() || undefined,
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        limit,
        offset: page * limit,
      });
      setIncidents(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load incidents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, [severityFilter, statusFilter, page]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(0);
    fetchIncidents();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>OPERATIONAL INCIDENT MANAGEMENT</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Incident Center
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Triage, investigate, and mitigate operational anomalies and degradation events.
          </p>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Showing <strong className="text-slate-200">{incidents.length}</strong> of{" "}
          <strong className="text-slate-200">{total}</strong> total incidents
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 backdrop-blur flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Search Input */}
        <form onSubmit={handleSearchSubmit} className="w-full md:w-80 relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search incident title, category..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:border-cyan-500/50"
          />
        </form>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-slate-700"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">SEV-1 Critical</option>
              <option value="HIGH">SEV-2 High</option>
              <option value="MEDIUM">SEV-3 Medium</option>
              <option value="LOW">SEV-4 Low</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-slate-700"
            >
              <option value="">All Statuses</option>
              <option value="INVESTIGATING">Investigating</option>
              <option value="OPEN">Open</option>
              <option value="MITIGATED">Mitigated</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>
        </div>
      </div>

      {/* Incident Table */}
      {loading ? (
        <TableSkeleton rows={6} cols={7} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchIncidents} />
      ) : incidents.length === 0 ? (
        <EmptyState
          title="No operational incidents found"
          description={
            search || severityFilter || statusFilter
              ? "No incidents matched your filter parameters. Try clearing your filters."
              : "Aegis has not detected any active incidents requiring operational attention."
          }
          actionLabel={
            search || severityFilter || statusFilter ? "Clear Filters" : undefined
          }
          onAction={() => {
            setSearch("");
            setSeverityFilter("");
            setStatusFilter("");
            setPage(0);
          }}
        />
      ) : (
        <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden backdrop-blur">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-slate-400 text-[11px] uppercase tracking-wider">
                  <th className="py-3 px-4">Severity</th>
                  <th className="py-3 px-4">Incident</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Affected Systems</th>
                  <th className="py-3 px-4">Detected</th>
                  <th className="py-3 px-4">Revenue Impact</th>
                  <th className="py-3 px-4">AI Confidence</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {incidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <SeverityBadge severity={inc.severity} size="sm" />
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/incidents/${inc.id}`}
                          className="font-sans font-medium text-slate-200 text-xs hover:text-cyan-400 transition-colors"
                        >
                          {inc.title}
                        </Link>
                        {inc.category && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 uppercase">
                            {inc.category}
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5 line-clamp-1">
                        {inc.summary}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusBadge status={inc.status} size="sm" />
                    </td>
                    <td className="py-3.5 px-4 text-cyan-300">
                      {inc.affected_systems?.join(", ") || "—"}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(inc.detected_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-rose-300 font-bold whitespace-nowrap">
                      ${inc.estimated_revenue_impact?.toLocaleString() || "0"}
                    </td>
                    <td className="py-3.5 px-4 text-emerald-400 whitespace-nowrap">
                      {inc.confidence ? `${Math.round(inc.confidence * 100)}%` : "—"}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
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

          {/* Pagination Footer */}
          {total > limit && (
            <div className="p-3 border-t border-slate-800 flex items-center justify-between text-xs font-mono text-slate-400">
              <div>
                Page {page + 1} of {Math.ceil(total / limit)}
              </div>
              <div className="flex gap-2">
                <button
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                  className="px-3 py-1 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={(page + 1) * limit >= total}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-3 py-1 rounded bg-slate-900 border border-slate-800 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
