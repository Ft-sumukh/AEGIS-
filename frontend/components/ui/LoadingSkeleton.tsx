import React from "react";

export function TableSkeleton({ rows = 5, cols = 6 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950/60 overflow-hidden animate-pulse">
      <div className="h-12 bg-slate-900/80 border-b border-slate-800 flex items-center px-6 gap-4">
        {Array.from({ length: cols }).map((_, i) => (
          <div key={i} className="h-4 bg-slate-800 rounded flex-1" />
        ))}
      </div>
      <div className="divide-y divide-slate-800/60 p-2">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="h-14 flex items-center px-4 gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <div
                key={c}
                className={`h-4 rounded ${
                  c === 0 ? "w-20 bg-slate-800" : c === 1 ? "w-48 bg-slate-800" : "flex-1 bg-slate-900"
                }`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function CardSkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse space-y-3"
        >
          <div className="h-3 w-28 bg-slate-800 rounded" />
          <div className="h-7 w-20 bg-slate-800 rounded mt-2" />
          <div className="h-3 w-36 bg-slate-800/60 rounded" />
        </div>
      ))}
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/40 animate-pulse space-y-4">
      <div className="flex items-center justify-between">
        <div className="h-4 w-40 bg-slate-800 rounded" />
        <div className="h-4 w-24 bg-slate-800 rounded" />
      </div>
      <div className="h-64 bg-slate-950/60 rounded border border-slate-800/60 flex items-end p-4 gap-2">
        {Array.from({ length: 16 }).map((_, i) => (
          <div
            key={i}
            className="flex-1 bg-slate-800/40 rounded-t"
            style={{ height: `${20 + ((i * 17) % 70)}%` }}
          />
        ))}
      </div>
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="p-6 rounded-xl border border-slate-800 bg-slate-900/50 space-y-4">
        <div className="h-6 w-1/3 bg-slate-800 rounded" />
        <div className="h-4 w-2/3 bg-slate-800/60 rounded" />
        <div className="flex gap-3 mt-4">
          <div className="h-7 w-24 bg-slate-800 rounded" />
          <div className="h-7 w-28 bg-slate-800 rounded" />
        </div>
      </div>
      <CardSkeleton count={4} />
      <ChartSkeleton />
    </div>
  );
}

export function LoadingSkeleton({ count = 4 }: { count?: number; rows?: number }) {
  return <CardSkeleton count={count} />;
}

