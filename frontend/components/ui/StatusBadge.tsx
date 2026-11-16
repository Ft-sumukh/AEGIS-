import React from "react";

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
  const norm = String(status).toUpperCase();

  let styles = "bg-slate-900 text-slate-300 border-slate-700";
  let pulse = false;

  switch (norm) {
    case "INVESTIGATING":
    case "RUNNING":
      styles = "bg-amber-950/40 text-amber-300 border-amber-800/60";
      pulse = true;
      break;
    case "OPEN":
    case "NEW":
      styles = "bg-cyan-950/40 text-cyan-300 border-cyan-800/60";
      break;
    case "MITIGATED":
    case "ACKNOWLEDGED":
      styles = "bg-blue-950/40 text-blue-300 border-blue-800/60";
      break;
    case "RESOLVED":
    case "COMPLETED":
    case "HEALTHY":
    case "SUPPORTED":
      styles = "bg-emerald-950/40 text-emerald-300 border-emerald-800/60";
      break;
    case "CLOSED":
    case "DISMISSED":
    case "REJECTED":
    case "FAILED":
      styles = "bg-slate-900/60 text-slate-400 border-slate-800";
      break;
    case "CRITICAL":
      styles = "bg-rose-950/40 text-rose-300 border-rose-800/60";
      pulse = true;
      break;
    case "DEGRADED":
      styles = "bg-amber-950/40 text-amber-300 border-amber-800/60";
      break;
    default:
      styles = "bg-slate-900 text-slate-300 border-slate-700";
  }

  const isSmall = size === "sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-mono border ${styles} ${
        isSmall ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs"
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          pulse ? "animate-ping opacity-75" : ""
        } ${
          norm === "INVESTIGATING" || norm === "CRITICAL"
            ? "bg-amber-400"
            : norm === "RESOLVED" || norm === "HEALTHY" || norm === "SUPPORTED"
            ? "bg-emerald-400"
            : norm === "OPEN"
            ? "bg-cyan-400"
            : "bg-slate-400"
        }`}
      />
      <span className="font-semibold uppercase tracking-wider">{status}</span>
    </span>
  );
}
