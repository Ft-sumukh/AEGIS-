"use client";

import { useEffect, useState } from "react";
import { apiClient, HealthStatus } from "@/lib/api";
import { Activity, AlertCircle, CheckCircle2, RefreshCw } from "lucide-react";

export function HealthBadge() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getHealth();
      setHealth(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect to backend");
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    // Poll every 30 seconds for live status
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono border bg-slate-900/80 backdrop-blur border-slate-800 shadow-sm">
      <span className="flex items-center gap-1.5 text-slate-400">
        <Activity className="w-3.5 h-3.5 text-slate-500" />
        <span className="hidden sm:inline">Backend:</span>
      </span>

      {loading && !health && !error ? (
        <span className="flex items-center gap-1 text-slate-400">
          <RefreshCw className="w-3 h-3 animate-spin text-slate-500" />
          <span>Connecting...</span>
        </span>
      ) : error ? (
        <span
          className="flex items-center gap-1.5 text-rose-400 font-medium cursor-help"
          title={`Backend Disconnected (${error})`}
        >
          <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
          <AlertCircle className="w-3 h-3" />
          <span>Offline</span>
        </span>
      ) : (
        <span
          className="flex items-center gap-1.5 text-emerald-400 font-medium cursor-help"
          title={`Connected to ${health?.service} v${health?.version} [${health?.environment}]`}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500" />
          <CheckCircle2 className="w-3 h-3" />
          <span>Online ({health?.version})</span>
        </span>
      )}

      <button
        onClick={checkHealth}
        aria-label="Refresh backend status"
        className="text-slate-500 hover:text-slate-300 transition-colors ml-0.5 p-0.5"
      >
        <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
      </button>
    </div>
  );
}
