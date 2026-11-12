"use client";

import React, { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { SearchModal } from "./SearchModal";
import { CoPilotDrawer } from "@/components/copilot/CoPilotDrawer";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { api } from "@/lib/api/client";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [activeIncidentsCount, setActiveIncidentsCount] = useState(0);
  const [lastUpdatedSecondsAgo, setLastUpdatedSecondsAgo] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pollingInterval, setPollingInterval] = useState<number | null>(30);

  const fetchOverviewStatus = async () => {
    try {
      const data = await api.getOverview();
      setActiveIncidentsCount(data.kpis.active_incidents);
      setLastUpdatedSecondsAgo(0);
    } catch {
      // Quiet
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchOverviewStatus();
    setIsRefreshing(false);
  };

  // Keyboard shortcut Cmd+K / Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Polling loop
  useEffect(() => {
    fetchOverviewStatus();
    if (pollingInterval === null) return;
    const interval = setInterval(fetchOverviewStatus, pollingInterval * 1000);
    return () => clearInterval(interval);
  }, [pollingInterval]);

  // Second ticker
  useEffect(() => {
    const ticker = setInterval(() => {
      setLastUpdatedSecondsAgo((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(ticker);
  }, []);

  return (
    <AuthProvider>
      <div className="flex min-h-screen bg-[#080c14] text-slate-100 antialiased selection:bg-cyan-500/20 selection:text-cyan-300">
        <Sidebar />
        <div className="flex flex-col flex-1 min-w-0">
          <TopBar
            activeIncidentsCount={activeIncidentsCount}
            lastUpdatedSecondsAgo={lastUpdatedSecondsAgo}
            isRefreshing={isRefreshing}
            onRefresh={handleRefresh}
            onOpenSearch={() => setSearchOpen(true)}
            pollingInterval={pollingInterval}
            onPollingIntervalChange={setPollingInterval}
          />
          <main className="flex-1 p-4 md:p-8 overflow-y-auto max-w-7xl mx-auto w-full">
            {children}
          </main>
        </div>
        <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
        <CoPilotDrawer />
      </div>
    </AuthProvider>
  );
}
