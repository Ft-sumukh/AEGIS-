"use client";

import React, { useEffect, useState } from "react";
import {
  Sliders,
  Server,
  Database,
  Key,
  Shield,
  Clock,
  Radio,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Cpu,
  Lock,
  HardDrive,
  Activity,
  Layers,
  Send,
  Trash2,
  Plus,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { SettingsData, WebhookSubscription } from "@/lib/api/types";
import { CardSkeleton } from "@/components/ui/LoadingSkeleton";
import { ErrorState } from "@/components/ui/ErrorState";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);
  const [newWebhookName, setNewWebhookName] = useState("");
  const [newWebhookUrl, setNewWebhookUrl] = useState("");
  const [newWebhookType, setNewWebhookType] = useState<"SLACK" | "PAGERDUTY" | "GENERIC_WEBHOOK">("SLACK");
  const [showAddWebhook, setShowAddWebhook] = useState(false);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      setError(null);
      const [settingsData, webhooksData] = await Promise.all([
        api.getSettings(),
        api.listWebhooks().catch(() => []),
      ]);
      setSettings(settingsData);
      setWebhooks(webhooksData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load platform settings");
    } finally {
      setLoading(false);
    }
  };

  const handleTestWebhook = async (id: string) => {
    try {
      setTestResult("Dispatching test alert probe...");
      const res = await api.testWebhook(id);
      setTestResult(`Test probe delivered: HTTP ${res.status_code || 200}`);
      fetchSettings();
    } catch (err: any) {
      setTestResult(`Test dispatch error: ${err.message}`);
    }
  };

  const handleAddWebhook = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createWebhook({
        name: newWebhookName,
        url: newWebhookUrl,
        target_type: newWebhookType,
      });
      setNewWebhookName("");
      setNewWebhookUrl("");
      setShowAddWebhook(false);
      fetchSettings();
    } catch (err: any) {
      alert(`Failed to add webhook: ${err.message}`);
    }
  };

  const handleDeleteWebhook = async (id: string) => {
    if (!confirm("Remove this webhook subscription?")) return;
    try {
      await api.deleteWebhook(id);
      fetchSettings();
    } catch (err: any) {
      alert(`Failed to delete webhook: ${err.message}`);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 mb-1">
            <Sliders className="w-3.5 h-3.5" />
            <span>PLATFORM CONFIGURATION & GOVERNANCE</span>
          </div>
          <h1 className="text-2xl font-bold font-mono tracking-tight text-white">
            Platform Settings
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Operational runtime parameters, AI governance constraints, privacy enforcement, and retention policies.
          </p>
        </div>

        <button
          onClick={fetchSettings}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-900/60 hover:bg-slate-800 text-xs font-mono text-slate-300 transition-colors w-fit"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : error ? (
        <ErrorState message={error} onRetry={fetchSettings} />
      ) : settings ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Section 1: System Environment & Runtime */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-cyan-950/60 border border-cyan-800/40 flex items-center justify-center text-cyan-400">
                <Server className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">System Runtime</h2>
                <p className="text-xs text-slate-400">Application build, environment and API endpoint</p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Platform Name:</span>
                <span className="text-slate-200 font-bold">{settings.app_name}</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Version:</span>
                <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-cyan-300">
                  {settings.app_version}
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Environment:</span>
                <span className="px-2 py-0.5 rounded bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 uppercase">
                  {settings.environment}
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Backend API URL:</span>
                <span className="text-slate-300 truncate max-w-[200px]">
                  {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-400">Role Simulation:</span>
                <span className="text-amber-300">RBAC Active (X-User-Role)</span>
              </div>
            </div>
          </div>

          {/* Section 2: AI Intelligence & Investigation Limits */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400">
                <Cpu className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">AI Intelligence & Limits</h2>
                <p className="text-xs text-slate-400">Safety thresholds for autonomous diagnostic agents</p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Provider / Model:</span>
                <span className="text-indigo-300 font-semibold">
                  {settings.ai_config.provider} ({settings.ai_config.model})
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Max Tool Calls per Run:</span>
                <span className="text-slate-200">{settings.ai_config.max_tool_calls_per_investigation} calls</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Max Context Records:</span>
                <span className="text-slate-200">{settings.ai_config.max_context_records} records</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Query Time Horizon:</span>
                <span className="text-slate-200">{settings.ai_config.max_query_window_hours} hours max</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-400">Investigation Timeout:</span>
                <span className="text-slate-200">{settings.ai_config.max_investigation_duration_seconds}s</span>
              </div>
            </div>
          </div>

          {/* Section 3: Data Policy & Governance */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-emerald-950/60 border border-emerald-800/40 flex items-center justify-center text-emerald-400">
                <Shield className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Data Governance & Privacy</h2>
                <p className="text-xs text-slate-400">Sanitization, PII redaction and controlled tool access</p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Governance Mode:</span>
                <span className="text-emerald-300 font-bold uppercase">{settings.data_policy.mode}</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">PII Field Redaction:</span>
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Active
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">HMAC-SHA256 Pseudonymization:</span>
                <span className="flex items-center gap-1.5 text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Salt Active
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Allowlisted Investigation Tools:</span>
                <span className="text-slate-200">{settings.data_policy.allowlisted_tools_count} read-only tools</span>
              </div>
              <div className="flex justify-between items-center py-1.5">
                <span className="text-slate-400">Arbitrary SQL Access:</span>
                <span className="flex items-center gap-1.5 text-rose-400">
                  <XCircle className="w-3.5 h-3.5" /> Strict Prohibition (Enforced)
                </span>
              </div>
            </div>
          </div>

          {/* Section 4: Data Retention & Telemetry Sources */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-amber-950/60 border border-amber-800/40 flex items-center justify-center text-amber-400">
                <HardDrive className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-slate-200">Retention & Telemetry</h2>
                <p className="text-xs text-slate-400">Telemetry corpus, data sources and lifecycle rules</p>
              </div>
            </div>

            <div className="space-y-2.5 text-xs font-mono">
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Audit Log Retention:</span>
                <span className="text-slate-200">{settings.retention_policy.audit_log_retention_days} days</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Investigation Data Retention:</span>
                <span className="text-slate-200">{settings.retention_policy.investigation_retention_days} days</span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Total Telemetry Volume:</span>
                <span className="text-amber-300 font-bold">
                  {settings.telemetry_sources.total_telemetry_records.toLocaleString()} records
                </span>
              </div>
              <div className="flex justify-between items-center py-1.5 border-b border-slate-800/60">
                <span className="text-slate-400">Data Quality Status:</span>
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/50">
                  {settings.telemetry_sources.quality_status}
                </span>
              </div>
              <div className="pt-1">
                <span className="text-slate-400 block mb-1.5">Active Ingestion Sources:</span>
                <div className="flex flex-wrap gap-1.5">
                  {settings.telemetry_sources.active_sources.map((src) => (
                    <span
                      key={src}
                      className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-[10px] text-slate-300"
                    >
                      {src}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Section 5: External Webhook Integrations Hub */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-5 space-y-4 md:col-span-2">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-indigo-950/60 border border-indigo-800/40 flex items-center justify-center text-indigo-400">
                  <Send className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-200">Alert Webhook Integrations (Slack / PagerDuty / Webhook)</h2>
                  <p className="text-xs text-slate-400">Outbound event dispatching with HMAC-SHA256 signature verification</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddWebhook(!showAddWebhook)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-indigo-600 rounded hover:bg-indigo-500 transition shadow"
              >
                <Plus className="w-3.5 h-3.5" /> Add Webhook
              </button>
            </div>

            {testResult && (
              <div className="p-2.5 rounded bg-slate-950 border border-indigo-800/60 text-xs font-mono text-indigo-300 flex items-center justify-between">
                <span>{testResult}</span>
                <button onClick={() => setTestResult(null)} className="text-slate-500 hover:text-slate-300">✕</button>
              </div>
            )}

            {showAddWebhook && (
              <form onSubmit={handleAddWebhook} className="p-4 rounded-lg bg-slate-950 border border-slate-800 space-y-3 text-xs">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-slate-400 mb-1">Target Name</label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. #ops-war-room"
                      value={newWebhookName}
                      onChange={(e) => setNewWebhookName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-200 outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Target Type</label>
                    <select
                      value={newWebhookType}
                      onChange={(e: any) => setNewWebhookType(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-200 outline-none"
                    >
                      <option value="SLACK">Slack Incoming Webhook</option>
                      <option value="PAGERDUTY">PagerDuty Events API v2</option>
                      <option value="GENERIC_WEBHOOK">Custom Generic Webhook</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-slate-400 mb-1">Webhook URL</label>
                    <input
                      type="url"
                      required
                      placeholder="https://hooks.slack.com/services/..."
                      value={newWebhookUrl}
                      onChange={(e) => setNewWebhookUrl(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded p-2 text-slate-200 outline-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowAddWebhook(false)}
                    className="px-3 py-1 text-slate-400 hover:text-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1 bg-indigo-600 text-white rounded hover:bg-indigo-500 font-medium"
                  >
                    Save Subscription
                  </button>
                </div>
              </form>
            )}

            {webhooks.length === 0 ? (
              <div className="py-6 text-center text-xs text-slate-500 bg-slate-950/40 rounded border border-slate-800/60">
                No external webhooks registered. Register a Slack or PagerDuty target to receive automated incident and SLO alerts.
              </div>
            ) : (
              <div className="space-y-2">
                {webhooks.map((sub) => (
                  <div
                    key={sub.id}
                    className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200">{sub.name}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-950 text-indigo-300 border border-indigo-800">
                          {sub.target_type}
                        </span>
                        {sub.last_status_code && (
                          <span className={`px-1.5 py-0.2 rounded text-[10px] font-mono ${
                            sub.last_status_code === 200 ? "bg-emerald-950 text-emerald-400" : "bg-rose-950 text-rose-400"
                          }`}>
                            HTTP {sub.last_status_code}
                          </span>
                        )}
                      </div>
                      <div className="text-slate-500 font-mono text-[11px] mt-0.5 truncate max-w-md">
                        {sub.url}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleTestWebhook(sub.id)}
                        className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-300 hover:bg-slate-800 transition font-medium"
                      >
                        Send Test Probe
                      </button>
                      <button
                        onClick={() => handleDeleteWebhook(sub.id)}
                        className="p-1 text-slate-500 hover:text-rose-400 transition"
                        title="Delete subscription"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
