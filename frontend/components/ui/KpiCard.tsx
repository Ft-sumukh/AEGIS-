import React from "react";
import { ArrowUpRight, ArrowDownRight, Minus } from "lucide-react";

interface KpiCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: number | null;
  trendDirection?: "up" | "down" | "neutral";
  comparisonPeriod?: string;
  status?: "normal" | "warning" | "critical" | "healthy";
  icon?: React.ElementType;
  subtitle?: string;
}

export function KpiCard({
  title,
  value,
  unit,
  trend,
  trendDirection,
  comparisonPeriod = "vs baseline",
  status = "normal",
  icon: Icon,
  subtitle,
}: KpiCardProps) {
  let statusDotColor = "bg-slate-500";
  let statusBorder = "border-slate-800";

  if (status === "critical") {
    statusDotColor = "bg-rose-500 animate-pulse";
    statusBorder = "border-rose-900/50 bg-rose-950/10";
  } else if (status === "warning") {
    statusDotColor = "bg-amber-500";
    statusBorder = "border-amber-900/50 bg-amber-950/10";
  } else if (status === "healthy") {
    statusDotColor = "bg-emerald-500";
    statusBorder = "border-slate-800 bg-slate-900/50";
  } else {
    statusBorder = "border-slate-800 bg-slate-900/40";
  }

  const isUp = trendDirection === "up" || (trend !== undefined && trend !== null && trend > 0);
  const isDown = trendDirection === "down" || (trend !== undefined && trend !== null && trend < 0);

  return (
    <div
      className={`p-5 rounded-xl border backdrop-blur transition-all hover:border-slate-700 ${statusBorder}`}
    >
      <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
          <span className="font-semibold tracking-wider uppercase">{title}</span>
        </div>
        {Icon && <Icon className="w-4 h-4 text-slate-400" />}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl md:text-3xl font-bold font-mono tracking-tight text-white">
          {value}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono font-medium">{unit}</span>}
      </div>

      <div className="mt-2.5 flex items-center justify-between text-xs">
        {trend !== undefined && trend !== null ? (
          <div
            className={`flex items-center gap-1 font-mono font-semibold ${
              status === "critical"
                ? "text-rose-400"
                : status === "warning"
                ? "text-amber-400"
                : isUp
                ? "text-cyan-400"
                : "text-emerald-400"
            }`}
          >
            {isUp ? (
              <ArrowUpRight className="w-3.5 h-3.5" />
            ) : isDown ? (
              <ArrowDownRight className="w-3.5 h-3.5" />
            ) : (
              <Minus className="w-3.5 h-3.5" />
            )}
            <span>
              {trend > 0 ? `+${trend}%` : `${trend}%`}
            </span>
            <span className="text-slate-400 font-sans font-normal ml-1 opacity-80">
              {comparisonPeriod}
            </span>
          </div>
        ) : subtitle ? (
          <span className="text-slate-400 font-sans text-xs">{subtitle}</span>
        ) : (
          <span className="text-slate-400 font-sans text-xs">{comparisonPeriod}</span>
        )}
      </div>
    </div>
  );
}
