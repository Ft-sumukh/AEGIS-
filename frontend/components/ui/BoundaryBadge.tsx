import React from "react";
import { CheckCircle2, Sparkles, Lightbulb } from "lucide-react";

export type BoundaryType = "FACT" | "ASSESSMENT" | "RECOMMENDATION" | "CORRELATION" | "HYPOTHESIS";

interface BoundaryBadgeProps {
  type: BoundaryType;
  className?: string;
}

export function BoundaryBadge({ type, className = "" }: BoundaryBadgeProps) {
  let label = "OBSERVED FACT";
  let styles = "bg-teal-950/40 text-teal-300 border-teal-800/60";
  let Icon = CheckCircle2;

  if (type === "ASSESSMENT") {
    label = "AI ASSESSMENT";
    styles = "bg-purple-950/40 text-purple-300 border-purple-800/60";
    Icon = Sparkles;
  } else if (type === "RECOMMENDATION") {
    label = "RECOMMENDATION";
    styles = "bg-amber-950/40 text-amber-300 border-amber-800/60";
    Icon = Lightbulb;
  } else if (type === "CORRELATION") {
    label = "CORRELATION (NON-CAUSAL)";
    styles = "bg-cyan-950/40 text-cyan-300 border-cyan-800/60";
    Icon = Sparkles;
  } else if (type === "HYPOTHESIS") {
    label = "HYPOTHESIS (UNVERIFIED)";
    styles = "bg-indigo-950/40 text-indigo-300 border-indigo-800/60";
    Icon = Lightbulb;
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold tracking-wider uppercase border ${styles} ${className}`}
      title={`Human-AI Classification: ${label}`}
    >
      <Icon className="w-3 h-3" />
      <span>{label}</span>
    </span>
  );
}
