"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  Cpu,
  LineChart,
  Layers,
  Lightbulb,
  ShieldCheck,
  Settings,
  Shield,
  Radio,
  Zap,
  GitCommit,
  Gauge,
} from "lucide-react";

import { api } from "@/lib/api/client";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string | number | null;
  badgeColor?: string;
}

export function Sidebar() {
  const pathname = usePathname();
  const [activeIncidentsCount, setActiveIncidentsCount] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;
    const loadIncidentCount = async () => {
      try {
        const res = await api.getOverview();
        if (isMounted) {
          setActiveIncidentsCount(res.kpis.active_incidents);
        }
      } catch {
        // Quiet fallback
      }
    };
    loadIncidentCount();
    const interval = setInterval(loadIncidentCount, 30000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const navItems: NavItem[] = [
    {
      name: "Overview",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Incidents",
      href: "/incidents",
      icon: AlertTriangle,
      badge: activeIncidentsCount !== null ? activeIncidentsCount : undefined,
      badgeColor:
        activeIncidentsCount && activeIncidentsCount > 0
          ? "bg-rose-950 text-rose-300 border-rose-800"
          : "bg-slate-900 text-slate-400 border-slate-800",
    },
    {
      name: "Investigations",
      href: "/investigations",
      icon: Cpu,
    },
    {
      name: "Analytics",
      href: "/analytics",
      icon: LineChart,
    },
    {
      name: "SLOs & Budgets",
      href: "/slos",
      icon: Gauge,
    },
    {
      name: "Traces",
      href: "/traces",
      icon: GitCommit,
    },
    {
      name: "Systems",
      href: "/systems",
      icon: Layers,
    },
    {
      name: "Recommendations",
      href: "/recommendations",
      icon: Lightbulb,
    },
    {
      name: "Actions",
      href: "/actions",
      icon: Zap,
    },
    {
      name: "Chaos Lab",
      href: "/chaos",
      icon: Radio,
    },
    {
      name: "Audit Trail",
      href: "/audit",
      icon: ShieldCheck,
    },
    {
      name: "Settings",
      href: "/settings",
      icon: Settings,
    },
  ];


  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-950 flex flex-col justify-between shrink-0 min-h-screen">
      <div>
        {/* Brand Header */}
        <Link
          href="/dashboard"
          className="h-16 px-6 flex items-center gap-3 border-b border-slate-800/80 bg-slate-950 hover:bg-slate-900/40 transition-colors"
        >
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shadow-[0_0_12px_rgba(6,182,212,0.15)]">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold tracking-wider text-slate-100 text-sm flex items-center gap-1.5">
              <span>AEGIS</span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                v0.2
              </span>
            </div>
            <p className="text-[11px] text-slate-400 tracking-tight">AI Operations Intelligence</p>
          </div>
        </Link>

        {/* Navigation Items */}
        <nav className="p-3 space-y-1">
          <div className="px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
            Platform Operations
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.08)]"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 border border-transparent"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-300"
                    }`}
                  />
                  <span>{item.name}</span>
                </div>
                {item.badge !== undefined && (
                  <span
                    className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      item.badgeColor || "bg-slate-900 text-slate-400 border-slate-800"
                    }`}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/50">
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2">
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400 flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-emerald-400 animate-pulse" />
              Intelligence
            </span>
            <span className="text-cyan-400 font-semibold">Active</span>
          </div>
          <div className="flex items-center justify-between text-[11px] font-mono">
            <span className="text-slate-400">Environment</span>
            <span className="text-slate-300">NovaCart Demo</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
