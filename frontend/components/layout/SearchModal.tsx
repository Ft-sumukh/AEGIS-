"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Search, X, AlertTriangle, Cpu, Layers, Activity } from "lucide-react";
import { api } from "@/lib/api/client";
import { SearchResultItem } from "@/lib/api/types";
import { SeverityBadge } from "@/components/ui/SeverityBadge";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setResults([]);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await api.search(query.trim());
        setResults(res.results);
        setSelectedIndex(0);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 200);

    return () => clearTimeout(timer);
  }, [query]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (results.length > 0 ? (prev + 1) % results.length : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) =>
        results.length > 0 ? (prev - 1 + results.length) % results.length : 0
      );
    } else if (e.key === "Enter" && results[selectedIndex]) {
      e.preventDefault();
      navigateTo(results[selectedIndex].url);
    }
  };

  const navigateTo = (url: string) => {
    onClose();
    router.push(url);
  };

  if (!isOpen) return null;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "incident":
        return <AlertTriangle className="w-4 h-4 text-rose-400" />;
      case "investigation":
        return <Cpu className="w-4 h-4 text-cyan-400" />;
      case "system":
        return <Layers className="w-4 h-4 text-emerald-400" />;
      case "anomaly":
        return <Activity className="w-4 h-4 text-amber-400" />;
      default:
        return <Search className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-start justify-center pt-20 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-xl rounded-xl border border-slate-700 bg-slate-950 shadow-2xl overflow-hidden animate-fadeIn"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 border-b border-slate-800 bg-slate-900/60">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            placeholder="Search incidents, investigations, systems, anomalies..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full bg-transparent px-3 py-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none font-mono"
          />
          {query && (
            <button onClick={() => setQuery("")} className="text-slate-400 hover:text-slate-200">
              <X className="w-4 h-4" />
            </button>
          )}
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 rounded border border-slate-700 ml-2">
            ESC
          </kbd>
        </div>

        {/* Results Body */}
        <div className="max-h-96 overflow-y-auto divide-y divide-slate-800/60 p-2">
          {isLoading ? (
            <div className="p-6 text-center text-xs font-mono text-slate-500">Searching operational index...</div>
          ) : results.length > 0 ? (
            results.map((res, index) => {
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={`${res.type}-${res.id}`}
                  onClick={() => navigateTo(res.url)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={`p-3 rounded-lg flex items-center justify-between cursor-pointer transition-colors ${
                    isSelected ? "bg-slate-900 border border-slate-700/80" : "hover:bg-slate-900/40 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="p-1.5 rounded bg-slate-900 border border-slate-800 shrink-0">
                      {getTypeIcon(res.type)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-slate-200 truncate flex items-center gap-2">
                        <span>{res.title}</span>
                        {res.severity && <SeverityBadge severity={res.severity} size="sm" showLabel={false} />}
                      </div>
                      {res.subtitle && (
                        <div className="text-[11px] text-slate-400 truncate mt-0.5">{res.subtitle}</div>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase text-slate-500 bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800 shrink-0 ml-3">
                    {res.type}
                  </span>
                </div>
              );
            })
          ) : query.trim() ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono">
              No operational records match &ldquo;{query}&rdquo;
            </div>
          ) : (
            <div className="p-6 text-center text-xs text-slate-500 font-mono space-y-1">
              <div>Type to search active incidents, services, and diagnostic runs</div>
              <div className="text-[11px] text-slate-600">e.g. &ldquo;checkout&rdquo;, &ldquo;database&rdquo;, &ldquo;anomaly&rdquo;</div>
            </div>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <div className="flex items-center gap-3">
            <span>↑↓ to navigate</span>
            <span>↵ to select</span>
          </div>
          <span>Aegis Search Index</span>
        </div>
      </div>
    </div>
  );
}
