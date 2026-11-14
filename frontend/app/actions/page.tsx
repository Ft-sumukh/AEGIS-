"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Zap,
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  Sliders,
  Server,
  Radio,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
  Info,
  CheckCheck,
} from "lucide-react";
import { api } from "@/lib/api/client";
import {
  ActionItem,
  ActionStatus,
  ActionType,
  SeverityLevel,
  ActionDefinition,
} from "@/lib/api/types";

export default function ActionQueuePage() {
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [definitions, setDefinitions] = useState<ActionDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [riskFilter, setRiskFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCatalog, setShowCatalog] = useState(false);

  useEffect(() => {
    loadData();
  }, [statusFilter, riskFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [actionsRes, defsRes] = await Promise.all([
        api.getActions({
          status: statusFilter !== "ALL" ? statusFilter : undefined,
          risk_level: riskFilter !== "ALL" ? riskFilter : undefined,
          limit: 100,
        }),
        api.getActionDefinitions().catch(() => []),
      ]);
      setActions(actionsRes.items || []);
      setDefinitions(defsRes || []);
    } catch (err) {
      console.error("Failed to load actions:", err);
    } finally {
      setLoading(false);
    }
  };

  const pendingCount = actions.filter((a) => a.status === "PENDING_APPROVAL").length;
  const approvedCount = actions.filter((a) => a.status === "APPROVED").length;
  const verifiedCount = actions.filter((a) => a.status === "VERIFIED").length;
  const executingCount = actions.filter(
    (a) => a.status === "EXECUTING" || a.status === "VERIFYING"
  ).length;

  const filteredActions = actions.filter((a) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.title.toLowerCase().includes(q) ||
      a.action_type.toLowerCase().includes(q) ||
      (a.target_service && a.target_service.toLowerCase().includes(q)) ||
      a.description.toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status: ActionStatus) => {
    switch (status) {
      case "PROPOSED":
        return "bg-slate-800 text-slate-300 border-slate-700";
      case "PENDING_APPROVAL":
        return "bg-amber-950/60 text-amber-300 border-amber-800 animate-pulse";
      case "APPROVED":
        return "bg-cyan-950/60 text-cyan-300 border-cyan-800";
      case "EXECUTING":
        return "bg-indigo-950/60 text-indigo-300 border-indigo-800 animate-pulse";
      case "EXECUTED":
        return "bg-blue-950/60 text-blue-300 border-blue-800";
      case "VERIFYING":
        return "bg-purple-950/60 text-purple-300 border-purple-800 animate-pulse";
      case "VERIFIED":
        return "bg-emerald-950/60 text-emerald-300 border-emerald-800";
      case "VERIFICATION_FAILED":
      case "FAILED":
        return "bg-rose-950/60 text-rose-300 border-rose-800";
      case "REJECTED":
        return "bg-zinc-900 text-zinc-400 border-zinc-800";
      case "EXPIRED":
        return "bg-slate-900 text-slate-500 border-slate-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getRiskBadge = (risk: SeverityLevel) => {
    switch (risk) {
      case "CRITICAL":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "HIGH":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "MEDIUM":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/30";
      case "LOW":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <Zap className="w-3 h-3" />
              Human-in-the-Loop Governance
            </span>
            <span className="text-xs text-slate-500">• Simulated Infrastructure Mode</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Operational Action Queue
          </h1>
          <p className="text-slate-400 text-sm mt-1 max-w-2xl">
            Controlled remediation engine. AI investigations propose actions, but execution is
            strictly gated by cryptographic fingerprinting, RBAC, and authenticated human approval.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCatalog(!showCatalog)}
            className="px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-sm font-medium flex items-center gap-2"
          >
            <Server className="w-4 h-4 text-cyan-400" />
            {showCatalog ? "Hide Capabilities" : "Action Catalog"}
          </button>
          <button
            onClick={loadData}
            className="px-3.5 py-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-600/30 transition-colors text-sm font-medium flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Pending Human Approval
            </span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2 flex items-baseline gap-2">
            {pendingCount}
            {pendingCount > 0 && (
              <span className="text-xs text-amber-400 font-medium animate-pulse">Action Required</span>
            )}
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Approved & Ready
            </span>
            <Play className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{approvedCount}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Executing / Verifying
            </span>
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{executingCount}</div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Verified Successful
            </span>
            <CheckCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white mt-2">{verifiedCount}</div>
        </div>
      </div>

      {/* Action Catalog Drawer */}
      {showCatalog && (
        <div className="bg-slate-900/80 border border-cyan-900/40 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white">
                Registered Operational Capabilities ({definitions.length})
              </h3>
            </div>
            <span className="text-xs text-slate-400">Execution Mode: STRICT SIMULATED</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {definitions.map((def) => (
              <div
                key={def.action_type}
                className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">{def.name}</span>
                  <span className={`px-1.5 py-0.5 rounded border text-[10px] ${getRiskBadge(def.risk_level)}`}>
                    {def.risk_level}
                  </span>
                </div>
                <p className="text-slate-400 leading-relaxed">{def.description}</p>
                <div className="pt-1 border-t border-slate-900 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Role: {def.required_role}</span>
                  <span>Approval: {def.requires_approval ? "Mandatory" : "Optional"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
        <div className="flex items-center gap-3 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search actions, services..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="PENDING_APPROVAL">Pending Approval</option>
            <option value="APPROVED">Approved</option>
            <option value="EXECUTING">Executing</option>
            <option value="EXECUTED">Executed</option>
            <option value="VERIFYING">Verifying</option>
            <option value="VERIFIED">Verified</option>
            <option value="REJECTED">Rejected</option>
            <option value="FAILED">Failed</option>
          </select>

          {/* Risk Filter */}
          <select
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            className="px-3 py-1.5 text-xs rounded-lg bg-slate-950 border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Risk Tiers</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div className="text-xs text-slate-500">
          Showing {filteredActions.length} of {actions.length} action proposals
        </div>
      </div>

      {/* Actions Table */}
      {loading ? (
        <div className="text-center py-16 space-y-3">
          <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-sm text-slate-400">Loading operational actions...</p>
        </div>
      ) : filteredActions.length === 0 ? (
        <div className="bg-slate-900/30 border border-slate-800 rounded-xl p-12 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 flex items-center justify-center mx-auto text-slate-500">
            <Zap className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-white">No actions found</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            No operational action proposals match the selected filters. Launch an AI investigation
            or propose an action from the recommendations tab.
          </p>
          <Link
            href="/recommendations"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600/20 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-600/30 text-sm font-medium transition-colors"
          >
            Browse Recommendations
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  <th className="py-3 px-4">Action & Type</th>
                  <th className="py-3 px-4">Target Service</th>
                  <th className="py-3 px-4">Risk Level</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Actors</th>
                  <th className="py-3 px-4">Timing</th>
                  <th className="py-3 px-4 text-right">Workflow</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-xs">
                {filteredActions.map((action) => (
                  <tr
                    key={action.id}
                    className="hover:bg-slate-800/30 transition-colors group"
                  >
                    <td className="py-3.5 px-4">
                      <div className="font-medium text-white group-hover:text-cyan-300 transition-colors">
                        {action.title}
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        {action.action_type}
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[11px]">
                        {action.target_service || "global"}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] font-semibold ${getRiskBadge(
                          action.risk_level
                        )}`}
                      >
                        {action.risk_level}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded-full border text-[11px] font-medium ${getStatusBadge(
                          action.status
                        )}`}
                      >
                        {action.status.replace(/_/g, " ")}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <div className="text-slate-300 font-mono text-[11px]">
                        Req: {action.requested_by}
                      </div>
                      {action.approved_by && (
                        <div className="text-emerald-400 font-mono text-[10px] mt-0.5">
                          App: {action.approved_by}
                        </div>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                      {new Date(action.requested_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/actions/${action.id}`}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                          action.status === "PENDING_APPROVAL"
                            ? "bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30"
                            : action.status === "APPROVED"
                            ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 hover:bg-cyan-500/30"
                            : action.status === "EXECUTED"
                            ? "bg-purple-500/20 text-purple-300 border-purple-500/40 hover:bg-purple-500/30"
                            : "bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700"
                        }`}
                      >
                        {action.status === "PENDING_APPROVAL"
                          ? "Authorize"
                          : action.status === "APPROVED"
                          ? "Execute"
                          : action.status === "EXECUTED"
                          ? "Verify"
                          : "Inspect"}
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
