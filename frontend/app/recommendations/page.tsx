"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Lightbulb,
  Filter,
  Search,
  ArrowRight,
  ShieldAlert,
  Info,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Clock,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { Recommendation } from "@/lib/api/types";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SeverityBadge } from "@/components/ui/SeverityBadge";
import { BoundaryBadge } from "@/components/ui/BoundaryBadge";
import { TableSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(0);
  const limit = 15;

  const fetchRecommendations = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getRecommendations({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        limit,
        offset: page * limit,
      });
      setRecommendations(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to load operational recommendations"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecommendations();
  }, [statusFilter, priorityFilter, page]);

  // Filter client-side by search query if typed
  const filteredItems = recommendations.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.title.toLowerCase().includes(q) ||
      (r.action_type && r.action_type.toLowerCase().includes(q)) ||
      r.description.toLowerCase().includes(q) ||
      r.incident_id.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-amber-400 mb-1">
            <Lightbulb className="w-3.5 h-3.5" />
            <span>OPERATIONAL REMEDIATION QUEUE</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Recommendations
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            AI-suggested mitigation plans, rollbacks, and capacity adjustments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchRecommendations}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs font-mono text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <div className="text-xs font-mono text-slate-400">
            Showing <strong className="text-slate-200">{filteredItems.length}</strong> of{" "}
            <strong className="text-slate-200">{total}</strong> items
          </div>
        </div>
      </div>

      {/* Scope Disclaimer Banner (Group 8 boundary) */}
      <div className="rounded-xl border border-amber-900/50 bg-amber-950/20 p-4 text-amber-300 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <div className="font-semibold font-mono tracking-wide text-amber-200">
            ADVISORY MODE ONLY — ACTION EXECUTION ENGINE (GROUP 9)
          </div>
          <p className="text-amber-300/80 leading-relaxed">
            All remediation plans below are strictly <strong>advisory recommendations</strong>.
            Aegis does not automatically trigger write-side actions, rollbacks, or service restarts in
            this console. Automated execution and human approval workflows will be enabled in{" "}
            <strong>Group 9 (Action & Human Approval Engine)</strong>.
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
            placeholder="Filter title, action, incident ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-100 placeholder-slate-500 font-mono focus:outline-none focus:border-amber-500/50"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 text-xs font-mono">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 focus:outline-none focus:border-amber-500"
            >
              <option value="">All Statuses</option>
              <option value="PROPOSED">Proposed</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="REJECTED">Rejected</option>
              <option value="EXECUTED">Executed</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs font-mono">
            <span className="text-slate-400">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => {
                setPriorityFilter(e.target.value);
                setPage(0);
              }}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1 focus:outline-none focus:border-amber-500"
            >
              <option value="">All Priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>

          {(statusFilter || priorityFilter || searchQuery) && (
            <button
              onClick={() => {
                setStatusFilter("");
                setPriorityFilter("");
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

      {/* Content Area */}
      {loading ? (
        <TableSkeleton rows={8} />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchRecommendations} />
      ) : filteredItems.length === 0 ? (
        <EmptyState
          title="No recommendations found"
          description="There are currently no remediation recommendations matching your filter criteria."
          actionLabel="Clear Filters"
          onAction={() => {
            setStatusFilter("");
            setPriorityFilter("");
            setSearchQuery("");
            setPage(0);
          }}
        />
      ) : (
        <div className="space-y-3">
          {filteredItems.map((rec) => (
            <div
              key={rec.id}
              className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 hover:border-slate-700 transition-all space-y-4"
            >
              {/* Header row */}
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <BoundaryBadge type="RECOMMENDATION" />
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-amber-400 uppercase font-semibold">
                      {(rec.action_type || rec.priority).replace(/_/g, " ")}
                    </span>
                    <SeverityBadge severity={rec.risk_level} size="sm" />
                    <StatusBadge status={rec.status} size="sm" />
                  </div>
                  <h3 className="text-base font-semibold text-slate-100">
                    {rec.title}
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed max-w-4xl">
                    {rec.description}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <Link
                    href={`/actions`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-cyan-800/80 bg-cyan-950/60 hover:bg-cyan-900/60 text-xs font-mono text-cyan-300 transition-colors"
                  >
                    <Zap className="w-3.5 h-3.5" />
                    <span>Action Queue</span>
                  </Link>
                  <Link
                    href={`/incidents/${rec.incident_id}`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 hover:bg-slate-900 text-xs font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
                  >
                    <span>View Incident</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </Link>
                </div>

              </div>

              {/* Impact and Metadata Box */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-3 rounded-lg bg-slate-950/70 border border-slate-800/80 text-xs font-mono">
                <div>
                  <span className="text-slate-500 block mb-0.5">EXPECTED IMPACT</span>
                  <span className="text-slate-300 font-sans text-xs">
                    {rec.expected_impact || "Reduces service error rate and stabilizes latency."}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5">PRIORITY / RISK</span>
                  <span className="text-slate-300">
                    Priority: <strong className="text-amber-300">{rec.priority}</strong> | Risk:{" "}
                    <strong className="text-slate-200">{rec.risk_level}</strong>
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block mb-0.5">CREATED</span>
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    {new Date(rec.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* Pagination */}
          <div className="flex items-center justify-between border-t border-slate-800/80 pt-4 px-1">
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
