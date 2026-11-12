import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Unable to load data",
  message = "An operational error occurred while communicating with the Aegis API.",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="rounded-xl border border-rose-900/50 bg-rose-950/10 p-8 text-center flex flex-col items-center justify-center">
      <div className="w-12 h-12 rounded-xl bg-rose-950/40 border border-rose-800/60 flex items-center justify-center text-rose-400 mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-semibold text-rose-200">{title}</h3>
      <p className="text-sm text-slate-400 mt-1 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-medium font-mono text-rose-300 bg-rose-950/60 border border-rose-800 hover:bg-rose-900/40 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Operation</span>
        </button>
      )}
    </div>
  );
}
