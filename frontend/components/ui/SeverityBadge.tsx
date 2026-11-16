import React from "react";
import { AlertOctagon, AlertTriangle, AlertCircle, Info } from "lucide-react";
import { SeverityLevel } from "@/lib/api/types";

interface SeverityBadgeProps {
  severity: SeverityLevel | string;
  size?: "sm" | "md";
  showLabel?: boolean;
}

export function SeverityBadge({
  severity,
  size = "sm",
  showLabel = true,
}: SeverityBadgeProps) {
  const norm = String(severity).toUpperCase();

  let config = {
    code: "SEV-4",
    name: "Low",
    bgColor: "bg-slate-900/80",
    borderColor: "border-slate-700",
    textColor: "text-slate-300",
    dotColor: "bg-slate-400",
    icon: Info,
  };

  if (norm === "CRITICAL" || norm === "SEV-1" || norm === "1") {
    config = {
      code: "SEV-1",
      name: "Critical",
      bgColor: "bg-rose-950/40",
      borderColor: "border-rose-700/60",
      textColor: "text-rose-300",
      dotColor: "bg-rose-500",
      icon: AlertOctagon,
    };
  } else if (norm === "HIGH" || norm === "SEV-2" || norm === "2") {
    config = {
      code: "SEV-2",
      name: "High",
      bgColor: "bg-amber-950/40",
      borderColor: "border-amber-700/60",
      textColor: "text-amber-300",
      dotColor: "bg-amber-500",
      icon: AlertTriangle,
    };
  } else if (norm === "MEDIUM" || norm === "SEV-3" || norm === "3") {
    config = {
      code: "SEV-3",
      name: "Medium",
      bgColor: "bg-yellow-950/40",
      borderColor: "border-yellow-700/60",
      textColor: "text-yellow-300",
      dotColor: "bg-yellow-500",
      icon: AlertCircle,
    };
  }

  const IconComponent = config.icon;
  const isSmall = size === "sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded font-mono font-medium border ${
        config.bgColor
      } ${config.borderColor} ${config.textColor} ${
        isSmall ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"
      }`}
      aria-label={`Severity ${config.code} - ${config.name}`}
    >
      <IconComponent className={isSmall ? "w-3 h-3" : "w-3.5 h-3.5"} />
      <span className="font-bold">{config.code}</span>
      {showLabel && <span className="opacity-80 font-sans text-[10px]">{config.name}</span>}
    </span>
  );
}
