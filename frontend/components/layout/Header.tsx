"use client";

import { Shield, Bell, Terminal } from "lucide-react";
import { HealthBadge } from "@/components/ui/HealthBadge";

export function Header() {
  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/60 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-30">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          <span>OPS-INTELLIGENCE // NODE-PRIMARY</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <HealthBadge />

        <div className="h-4 w-px bg-slate-800" />

        <button
          className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-900 rounded-lg transition-colors relative"
          aria-label="Notifications"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-cyan-500 absolute top-1.5 right-1.5" />
        </button>

        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
          <div className="w-7 h-7 rounded bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-semibold text-cyan-400">
            AE
          </div>
          <span className="text-xs font-medium text-slate-300 hidden md:inline">SecOps Admin</span>
        </div>
      </div>
    </header>
  );
}
