"use client";

import React, { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clock,
  RefreshCw,
  Search,
  Shield,
  UserCheck,
} from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { UserRole } from "@/lib/api/types";
import { HealthBadge } from "@/components/ui/HealthBadge";
import { useLiveEvents } from "@/lib/hooks/useLiveEvents";

interface TopBarProps {
  activeIncidentsCount?: number;
  lastUpdatedSecondsAgo?: number;
  isRefreshing?: boolean;
  onRefresh?: () => void;
  onOpenSearch?: () => void;
  pollingInterval?: number | null;
  onPollingIntervalChange?: (val: number | null) => void;
}

export function TopBar({
  activeIncidentsCount = 0,
  lastUpdatedSecondsAgo = 0,
  isRefreshing = false,
  onRefresh,
  onOpenSearch,
  pollingInterval = 30,
  onPollingIntervalChange,
}: TopBarProps) {
  const { role, setRole } = useAuth();
  const [roleMenuOpen, setRoleMenuOpen] = useState(false);
  const [latestAlert, setLatestAlert] = useState<string | null>(null);

  const { connected } = useLiveEvents({
    onEvent: (event) => {
      if (
        event.type === "INCIDENT_CREATED" ||
        event.type === "CHAOS_FAULT_INJECTED" ||
        event.type === "ACTION_APPROVED"
      ) {
        setLatestAlert(`Live: ${event.type.replace(/_/g, " ")}`);
        setTimeout(() => setLatestAlert(null), 5000);
      }
    },
  });

  const roles: UserRole[] = ["VIEWER", "ANALYST", "OPERATOR", "ADMIN"];

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-4 md:px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Left: Operational Indicators */}
      <div className="flex items-center gap-2 sm:gap-4 overflow-x-auto py-1">
        {/* Aegis Status Indicator */}
        <div className="flex items-center gap-2 text-xs font-mono text-slate-300 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded shrink-0">
          <span className={`w-2 h-2 rounded-full ${connected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
          <span className="font-semibold text-slate-200 hidden sm:inline">Aegis Operational</span>
          <span className="text-slate-500 font-sans hidden md:inline">|</span>
          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${connected ? "bg-emerald-950/80 text-emerald-400 border border-emerald-800/40" : "bg-amber-950/80 text-amber-400 border border-amber-800/40"}`}>
            {connected ? "LIVE SSE" : "CONNECTING"}
          </span>
        </div>

        {/* Live Event Flash Alert */}
        {latestAlert && (
          <div className="flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded shrink-0 border bg-cyan-950/80 text-cyan-300 border-cyan-800 animate-bounce">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
            <span className="font-semibold">{latestAlert}</span>
          </div>
        )}

        {/* Active Incident Counter Pill */}
        <div
          className={`flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded shrink-0 border ${
            activeIncidentsCount > 0
              ? "bg-rose-950/40 text-rose-300 border-rose-800/60"
              : "bg-slate-900 text-emerald-400 border-slate-800"
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          <span className="font-bold">{activeIncidentsCount}</span>
          <span className="hidden sm:inline">
            {activeIncidentsCount === 1 ? "Active Incident" : "Active Incidents"}
          </span>
        </div>

        {/* Telemetry Age */}
        <div className="hidden lg:flex items-center gap-1.5 text-[11px] font-mono text-slate-400">
          <Clock className="w-3 h-3 text-slate-500" />
          <span>
            Updated {lastUpdatedSecondsAgo < 5 ? "just now" : `${lastUpdatedSecondsAgo}s ago`}
          </span>
        </div>
      </div>

      {/* Right: Actions, Search, Role Selector */}
      <div className="flex items-center gap-2 sm:gap-3 shrink-0">
        {/* Global Search Button */}
        <button
          onClick={onOpenSearch}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/80 text-xs font-mono text-slate-400 hover:text-slate-200 hover:border-slate-700 transition-colors"
          title="Global Operational Search (Ctrl+K / Cmd+K)"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="hidden md:inline">Search...</span>
          <kbd className="hidden md:inline-block px-1.5 py-0.5 text-[9px] bg-slate-800 rounded border border-slate-700 text-slate-400">
            ⌘K
          </kbd>
        </button>

        {/* Refresh & Polling Interval */}
        {onRefresh && (
          <div className="flex items-center rounded-lg border border-slate-800 bg-slate-900/80 p-0.5 text-xs font-mono">
            <button
              onClick={onRefresh}
              className={`p-1.5 rounded text-slate-400 hover:text-cyan-400 transition-colors ${
                isRefreshing ? "animate-spin text-cyan-400" : ""
              }`}
              title="Refresh telemetry"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            {onPollingIntervalChange && (
              <select
                value={pollingInterval === null ? "pause" : String(pollingInterval)}
                onChange={(e) => {
                  const v = e.target.value;
                  onPollingIntervalChange(v === "pause" ? null : Number(v));
                }}
                className="bg-transparent text-[11px] font-mono text-slate-400 focus:outline-none pr-1 pl-1 cursor-pointer"
                title="Polling interval"
              >
                <option value="10" className="bg-slate-900 text-slate-300">10s</option>
                <option value="30" className="bg-slate-900 text-slate-300">30s</option>
                <option value="60" className="bg-slate-900 text-slate-300">60s</option>
                <option value="pause" className="bg-slate-900 text-slate-300">Paused</option>
              </select>
            )}
          </div>
        )}

        <HealthBadge />

        <div className="h-4 w-px bg-slate-800 hidden sm:block" />

        {/* Role Selector Dropdown for live RBAC demonstration */}
        <div className="relative">
          <button
            onClick={() => setRoleMenuOpen(!roleMenuOpen)}
            className="flex items-center gap-2 pl-2 pr-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900/60 hover:border-slate-700 text-xs font-mono transition-colors"
            title="Switch User Role Context (Server-Side RBAC Demonstration)"
          >
            <div className="w-6 h-6 rounded bg-cyan-950/60 border border-cyan-800/60 flex items-center justify-center text-[10px] font-bold text-cyan-400">
              {role.slice(0, 2)}
            </div>
            <div className="text-left hidden sm:block">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest leading-none">Role</div>
              <div className="text-xs font-semibold text-slate-200 leading-tight">{role}</div>
            </div>
          </button>

          {roleMenuOpen && (
            <div
              className="absolute right-0 mt-2 w-48 rounded-xl border border-slate-800 bg-slate-950 p-1.5 shadow-2xl z-50 animate-fadeIn"
              onClick={() => setRoleMenuOpen(false)}
            >
              <div className="px-3 py-1.5 text-[10px] font-mono uppercase text-slate-500 font-semibold tracking-wider">
                Simulated User Role
              </div>
              {roles.map((r) => (
                <button
                  key={r}
                  onClick={() => setRole(r)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-mono flex items-center justify-between transition-colors ${
                    role === r
                      ? "bg-cyan-950/40 text-cyan-300 border border-cyan-800/40"
                      : "text-slate-300 hover:bg-slate-900"
                  }`}
                >
                  <span>{r}</span>
                  {role === r && <UserCheck className="w-3.5 h-3.5 text-cyan-400" />}
                </button>
              ))}
              <div className="mt-1 pt-1 border-t border-slate-800 px-3 py-1 text-[10px] text-slate-500">
                Server enforces permissions via X-User-Role header
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
