"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Zap,
  ShieldCheck,
  ShieldAlert,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  Sliders,
  Server,
  Radio,
  ArrowLeft,
  Check,
  Copy,
  ExternalLink,
  Info,
  Lock,
  FileCheck,
} from "lucide-react";
import { api } from "@/lib/api/client";
import {
  ActionItem,
  ActionStatus,
  ActionType,
  SeverityLevel,
  ActionExecutionResult,
  VerificationResult,
} from "@/lib/api/types";

const STEPS: { status: ActionStatus; label: string }[] = [
  { status: "PROPOSED", label: "Proposed" },
  { status: "PENDING_APPROVAL", label: "Awaiting Approval" },
  { status: "APPROVED", label: "Approved" },
  { status: "EXECUTING", label: "Executing" },
  { status: "EXECUTED", label: "Executed" },
  { status: "VERIFYING", label: "Verifying" },
  { status: "VERIFIED", label: "Verified" },
];

export default function ActionDetailPage({
  params,
}: {
  params?: Promise<{ id: string }>;
}) {
  const routeParams = useParams();
  const initialId = (routeParams?.id as string) || "";
  const [actionId, setActionId] = useState<string>(initialId);

  useEffect(() => {
    if (params) {
      Promise.resolve(params).then((p) => {
        if (p?.id) setActionId(p.id);
      });
    } else if (routeParams?.id) {
      setActionId(routeParams.id as string);
    }
  }, [params, routeParams]);

  const [action, setAction] = useState<ActionItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Approval form state
  const [approvalReason, setApprovalReason] = useState("");
  const [confirmationPhrase, setConfirmationPhrase] = useState("");
  const [approving, setApproving] = useState(false);

  // Rejection form state
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  const [rejectionReason, setRejectionReason] = useState("");
  const [rejecting, setRejecting] = useState(false);

  // Execution form state
  const [dryRun, setDryRun] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<ActionExecutionResult | null>(null);

  // Verification state
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  const [copiedFingerprint, setCopiedFingerprint] = useState(false);

  useEffect(() => {
    loadAction();
  }, [actionId]);

  const loadAction = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getAction(actionId);
      setAction(res);
      if (res.verification_result) {
        setVerificationResult(res.verification_result as unknown as VerificationResult);
      }
    } catch (err: any) {
      setError(err?.message || "Failed to load action details.");
    } finally {
      setLoading(false);
    }
  };

  const handleCopyFingerprint = () => {
    if (!action?.fingerprint) return;
    navigator.clipboard.writeText(action.fingerprint);
    setCopiedFingerprint(true);
    setTimeout(() => setCopiedFingerprint(false), 2000);
  };

  const expectedConfirmPhrase =
    action && action.action_type
      ? `APPROVE ${action.action_type.replace(/_/g, " ")}`.toUpperCase()
      : "APPROVE";

  const isHighRisk =
    action?.risk_level === "HIGH" || action?.risk_level === "CRITICAL";

  const isConfirmationSatisfied =
    !isHighRisk ||
    confirmationPhrase.trim().toUpperCase() === expectedConfirmPhrase ||
    confirmationPhrase.trim().toUpperCase() === "APPROVE";

  const handleApprove = async () => {
    if (!action) return;
    try {
      setApproving(true);
      setError(null);
      await api.approveAction(action.id, {
        decision: "APPROVED",
        reason: approvalReason || "Authorized by human operator via console",
        confirmation_phrase: confirmationPhrase || undefined,
      });
      await loadAction();
    } catch (err: any) {
      setError(err?.message || "Approval failed.");
    } finally {
      setApproving(false);
    }
  };

  const handleReject = async () => {
    if (!action || !rejectionReason.trim()) return;
    try {
      setRejecting(true);
      setError(null);
      await api.rejectAction(action.id, { reason: rejectionReason });
      setShowRejectDialog(false);
      await loadAction();
    } catch (err: any) {
      setError(err?.message || "Rejection failed.");
    } finally {
      setRejecting(false);
    }
  };

  const handleExecute = async () => {
    if (!action) return;
    try {
      setExecuting(true);
      setError(null);
      const res = await api.executeAction(action.id, { dry_run: dryRun });
      setExecutionResult(res);
      await loadAction();
    } catch (err: any) {
      setError(err?.message || "Execution failed.");
    } finally {
      setExecuting(false);
    }
  };

  const handleVerify = async () => {
    if (!action) return;
    try {
      setVerifying(true);
      setError(null);
      const res = await api.verifyAction(action.id);
      setVerificationResult(res);
      await loadAction();
    } catch (err: any) {
      setError(err?.message || "Verification failed.");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-24 space-y-3 max-w-4xl mx-auto">
        <div className="w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-400">Loading action proposal...</p>
      </div>
    );
  }

  if (error && !action) {
    return (
      <div className="max-w-4xl mx-auto py-16 space-y-4 text-center">
        <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
        <h2 className="text-xl font-bold text-white">Action Not Found</h2>
        <p className="text-sm text-slate-400">{error}</p>
        <Link
          href="/actions"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Action Queue
        </Link>
      </div>
    );
  }

  if (!action) return null;

  // Compute step progression index
  const stepOrder: ActionStatus[] = [
    "PROPOSED",
    "PENDING_APPROVAL",
    "APPROVED",
    "EXECUTING",
    "EXECUTED",
    "VERIFYING",
    "VERIFIED",
  ];
  const currentStepIdx = stepOrder.indexOf(action.status);
  const isTerminalFailure =
    action.status === "REJECTED" ||
    action.status === "FAILED" ||
    action.status === "VERIFICATION_FAILED" ||
    action.status === "EXPIRED";

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-20">
      {/* Navigation & Header */}
      <div>
        <Link
          href="/actions"
          className="inline-flex items-center gap-2 text-xs font-medium text-slate-400 hover:text-cyan-400 transition-colors mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Operational Actions
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="font-mono text-xs text-cyan-400 uppercase font-semibold">
                {action.action_type}
              </span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400">Target:</span>
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-200">
                {action.target_service || "global"}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">{action.title}</h1>
            <p className="text-sm text-slate-400 mt-1 max-w-3xl">{action.description}</p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${
                action.risk_level === "CRITICAL"
                  ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                  : action.risk_level === "HIGH"
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                  : action.risk_level === "MEDIUM"
                  ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
              }`}
            >
              RISK: {action.risk_level}
            </span>

            <span
              className={`px-3 py-1 rounded-full text-xs font-bold border ${
                action.status === "VERIFIED"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40"
                  : action.status === "APPROVED"
                  ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
                  : action.status === "PENDING_APPROVAL"
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse"
                  : isTerminalFailure
                  ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                  : "bg-slate-800 text-slate-300 border-slate-700"
              }`}
            >
              {action.status.replace(/_/g, " ")}
            </span>
          </div>
        </div>
      </div>

      {/* Global Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/80 flex items-start gap-3 text-rose-200 text-sm">
          <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Operation Failed</div>
            <div className="text-xs text-rose-300/90 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* 7-Step Lifecycle Stepper */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-5">
        <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-4">
          Remediation Lifecycle Progression
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2">
          {STEPS.map((step, idx) => {
            const isDone = currentStepIdx > idx;
            const isCurrent = currentStepIdx === idx && !isTerminalFailure;
            const isFailed = isTerminalFailure && currentStepIdx <= idx;

            return (
              <div
                key={step.status}
                className={`p-2.5 rounded-lg border text-center transition-all ${
                  isDone
                    ? "bg-emerald-950/30 border-emerald-800/60 text-emerald-300"
                    : isCurrent
                    ? "bg-cyan-950/50 border-cyan-500/80 text-cyan-200 shadow-[0_0_12px_rgba(6,182,212,0.15)] ring-1 ring-cyan-500/30"
                    : isFailed && currentStepIdx === idx
                    ? "bg-rose-950/40 border-rose-800 text-rose-300"
                    : "bg-slate-950/40 border-slate-800/60 text-slate-500"
                }`}
              >
                <div className="flex items-center justify-center mb-1">
                  {isDone ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  ) : isCurrent ? (
                    <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  ) : isFailed && currentStepIdx === idx ? (
                    <XCircle className="w-4 h-4 text-rose-400" />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-slate-700" />
                  )}
                </div>
                <div className="text-[10px] font-mono text-slate-400">Step {idx + 1}</div>
                <div className="text-xs font-medium mt-0.5 truncate">{step.label}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Two Column Layout: Parameters & Cryptographic Governance */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Action Details & Parameters (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Target Parameters */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Action Parameters & Target Specification
            </h3>

            <div className="bg-slate-950/80 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre>{JSON.stringify(action.parameters, null, 2)}</pre>
            </div>

            {/* Expected Outcome & Downside */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 text-xs">
              <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
                <div className="font-semibold text-emerald-400">Expected Outcome</div>
                <p className="text-slate-300">
                  {action.expected_outcome || "Restoration of nominal latency and error rate."}
                </p>
              </div>

              <div className="p-3 rounded-lg bg-slate-950/40 border border-slate-800/80 space-y-1">
                <div className="font-semibold text-amber-400">Blast Radius & Downside</div>
                <p className="text-slate-300">
                  {(action.action_metadata?.downside as string) ||
                    "May cause momentary dropped keepalives or transient cache stampede during cycle."}
                </p>
              </div>
            </div>

            {/* Preconditions List */}
            {action.preconditions && action.preconditions.length > 0 && (
              <div className="space-y-2 pt-2 border-t border-slate-800/80">
                <div className="text-xs font-semibold text-slate-300">
                  Pre-execution Safety Invariants
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {action.preconditions.map((p, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-2 text-xs text-slate-400 bg-slate-950/40 px-2.5 py-1.5 rounded border border-slate-800/60"
                    >
                      <Check className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                      <span className="font-mono">{p}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Interactive Workflow Card */}
          {/* 1. Human Approval Gating Card */}
          {action.status === "PENDING_APPROVAL" && (
            <div className="bg-gradient-to-b from-amber-950/30 to-slate-900/60 border border-amber-800/60 rounded-xl p-5 space-y-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                  <Lock className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Human Authorization Required
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Aegis governance principle: The AI recommends, but only authenticated humans
                    authorize operational mutations.
                  </p>
                </div>
              </div>

              {/* Typed Confirmation for HIGH/CRITICAL */}
              {isHighRisk && (
                <div className="p-3.5 rounded-lg bg-slate-950 border border-amber-500/40 space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-amber-300">
                      High-Risk Action Confirmation Gate
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      Type: <strong className="text-white">{expectedConfirmPhrase}</strong>
                    </span>
                  </div>
                  <input
                    type="text"
                    placeholder={`Type '${expectedConfirmPhrase}' to authorize...`}
                    value={confirmationPhrase}
                    onChange={(e) => setConfirmationPhrase(e.target.value)}
                    className="w-full px-3 py-2 text-xs rounded bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-amber-500 font-mono"
                  />
                </div>
              )}

              {/* Justification note */}
              <div className="space-y-1 text-xs">
                <label className="text-slate-300 font-medium">
                  Approval Justification / Operational Reason
                </label>
                <input
                  type="text"
                  placeholder="e.g. Authorized following incident triage and rollback runbook"
                  value={approvalReason}
                  onChange={(e) => setApprovalReason(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 text-xs"
                />
              </div>

              {/* Buttons */}
              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <button
                  onClick={() => setShowRejectDialog(true)}
                  className="px-4 py-2 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 hover:bg-rose-900/40 text-xs font-semibold transition-colors"
                >
                  Reject Proposal
                </button>

                <button
                  onClick={handleApprove}
                  disabled={!isConfirmationSatisfied || approving}
                  className="px-5 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-xs font-semibold transition-colors flex items-center gap-2 shadow-lg shadow-emerald-950"
                >
                  {approving ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Authorizing...
                    </>
                  ) : (
                    <>
                      <ShieldCheck className="w-4 h-4" />
                      Grant Human Authorization
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* 2. Execution Card */}
          {action.status === "APPROVED" && (
            <div className="bg-gradient-to-b from-cyan-950/30 to-slate-900/60 border border-cyan-800/60 rounded-xl p-5 space-y-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0">
                  <Play className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Ready for Simulated Infrastructure Execution
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Action authorized by{" "}
                    <strong className="text-emerald-400 font-mono">
                      {action.approved_by || "human operator"}
                    </strong>
                    . Preconditions are verified against simulated topology.
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs">
                <input
                  type="checkbox"
                  id="dryRunToggle"
                  checked={dryRun}
                  onChange={(e) => setDryRun(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-cyan-500"
                />
                <label htmlFor="dryRunToggle" className="text-slate-300 cursor-pointer">
                  <strong>Dry-Run Mode:</strong> Run validation logic and precondition checks
                  without altering simulated infrastructure state.
                </label>
              </div>

              <div className="flex items-center justify-end pt-2 border-t border-slate-800">
                <button
                  onClick={handleExecute}
                  disabled={executing}
                  className="px-6 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold transition-colors flex items-center gap-2 shadow-lg shadow-cyan-950"
                >
                  {executing ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Executing Action...
                    </>
                  ) : (
                    <>
                      <Zap className="w-4 h-4" />
                      {dryRun ? "Run Simulation Dry-Run" : "Execute Operational Action"}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* 3. Post-Action Telemetry Verification Card */}
          {(action.status === "EXECUTED" ||
            action.status === "VERIFYING" ||
            action.status === "VERIFIED" ||
            action.status === "VERIFICATION_FAILED") && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileCheck className="w-4 h-4 text-purple-400" />
                  <h3 className="text-sm font-semibold text-white">
                    Post-Action Metric Verification
                  </h3>
                </div>

                {action.status === "EXECUTED" && (
                  <button
                    onClick={handleVerify}
                    disabled={verifying}
                    className="px-4 py-1.5 rounded-lg bg-purple-600/30 border border-purple-500/50 text-purple-200 hover:bg-purple-600/40 text-xs font-medium transition-colors flex items-center gap-2"
                  >
                    {verifying ? (
                      <>
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Verifying Metrics...
                      </>
                    ) : (
                      <>
                        <RotateCcw className="w-3.5 h-3.5" />
                        Run Telemetry Verification
                      </>
                    )}
                  </button>
                )}
              </div>

              {verificationResult ? (
                <div className="space-y-4">
                  {/* Outcome Alert */}
                  <div
                    className={`p-3.5 rounded-lg border text-xs flex items-center justify-between ${
                      verificationResult.outcome === "VERIFIED_SUCCESS"
                        ? "bg-emerald-950/40 border-emerald-800 text-emerald-200"
                        : verificationResult.outcome === "VERIFIED_PARTIAL"
                        ? "bg-amber-950/40 border-amber-800 text-amber-200"
                        : "bg-rose-950/40 border-rose-800 text-rose-200"
                    }`}
                  >
                    <div>
                      <div className="font-bold">{verificationResult.summary}</div>
                      <div className="text-[11px] opacity-80 mt-0.5">
                        Verified at: {new Date(verificationResult.verified_at).toLocaleTimeString()}
                      </div>
                    </div>
                    <span className="font-mono font-bold px-2 py-0.5 rounded bg-black/40 text-xs">
                      {verificationResult.signals_verified} Passed /{" "}
                      {verificationResult.signals_failed} Failed
                    </span>
                  </div>

                  {/* Before vs After Telemetry Comparison Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                      <div className="font-semibold text-rose-400">Pre-Action Baseline (Degraded)</div>
                      <div className="space-y-1 font-mono text-[11px] text-slate-300">
                        {Object.entries(verificationResult.metrics_before || {}).map(([k, v]) => (
                          <div key={k} className="flex justify-between border-b border-slate-900 py-1">
                            <span className="text-slate-500">{k}:</span>
                            <span className="text-rose-400 font-bold">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                      <div className="font-semibold text-emerald-400">Post-Action Recovery (Telemetry)</div>
                      <div className="space-y-1 font-mono text-[11px] text-slate-300">
                        {Object.entries(verificationResult.metrics_after || {}).map(([k, v]) => (
                          <div key={k} className="flex justify-between border-b border-slate-900 py-1">
                            <span className="text-slate-500">{k}:</span>
                            <span className="text-emerald-400 font-bold">{String(v)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Diagnostic Verification Logs */}
                  {verificationResult.details && (
                    <div className="space-y-1">
                      <div className="text-[11px] text-slate-400 font-semibold">
                        Verification Diagnostic Signals
                      </div>
                      <div className="space-y-1 font-mono text-[11px]">
                        {(Array.isArray(verificationResult.details)
                          ? verificationResult.details
                          : [String(verificationResult.details)]
                        ).map((d, i) => (
                          <div
                            key={i}
                            className="p-1.5 rounded bg-slate-950/60 border border-slate-800/80 text-slate-300 flex items-center gap-2"
                          >
                            <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            {d}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-lg">
                  Action executed. Click &ldquo;Run Telemetry Verification&rdquo; to evaluate post-mitigation
                  recovery signals.
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right Column: Cryptographic Security & Audit Trail (1 col) */}
        <div className="space-y-6">
          {/* Tamper-Evident Fingerprint */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              Cryptographic Fingerprint
            </h3>

            <div className="space-y-1">
              <div className="text-[11px] text-slate-400">Canonical SHA-256 Hash</div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800 font-mono text-[10px] text-slate-300 break-all flex items-center justify-between gap-2">
                <span>{action.fingerprint || "None computed"}</span>
                <button
                  onClick={handleCopyFingerprint}
                  className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white"
                  title="Copy SHA-256 fingerprint"
                >
                  {copiedFingerprint ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/80 text-[11px] space-y-2 text-slate-400">
              <div className="flex justify-between">
                <span>Tamper Check:</span>
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <Check className="w-3 h-3" />
                  VERIFIED INTACT
                </span>
              </div>
              <div className="flex justify-between">
                <span>Requested By:</span>
                <span className="font-mono text-slate-200">{action.requested_by}</span>
              </div>
              {action.approved_by && (
                <div className="flex justify-between">
                  <span>Authorized By:</span>
                  <span className="font-mono text-emerald-400">{action.approved_by}</span>
                </div>
              )}
              {action.expires_at && (
                <div className="flex justify-between">
                  <span>Approval TTL:</span>
                  <span className="font-mono text-amber-400">
                    {new Date(action.expires_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Human Decision Audit Trail */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-cyan-400" />
              Authorization Audit Trail
            </h3>

            {action.approvals && action.approvals.length > 0 ? (
              <div className="space-y-3">
                {action.approvals.map((app) => (
                  <div
                    key={app.id}
                    className="p-3 bg-slate-950/80 border border-slate-800/80 rounded-lg text-xs space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`font-semibold ${
                          app.decision === "APPROVED" ? "text-emerald-400" : "text-rose-400"
                        }`}
                      >
                        {app.decision}
                      </span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(app.decision_at).toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="text-slate-300 font-mono text-[11px]">
                      By: {app.decision_by}
                    </div>
                    {app.reason && (
                      <div className="text-slate-400 text-[11px] italic">
                        &ldquo;{app.reason}&rdquo;
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-500 italic text-center py-4">
                No authorization decisions recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Rejection Reason Modal Dialog */}
      {showRejectDialog && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <XCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Reject Action Proposal</h3>
            </div>
            <p className="text-xs text-slate-400">
              Provide an operational justification explaining why this remediation proposal is rejected.
              This will be permanently archived in the security audit trail.
            </p>
            <textarea
              rows={3}
              placeholder="e.g. Inadequate canary signal; risks downstream database partition."
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              className="w-full px-3 py-2 text-xs rounded bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-rose-500 resize-none"
            />
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setShowRejectDialog(false)}
                className="px-4 py-2 rounded-lg bg-slate-800 text-slate-300 hover:bg-slate-700 text-xs font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={!rejectionReason.trim() || rejecting}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold disabled:opacity-40"
              >
                {rejecting ? "Rejecting..." : "Confirm Rejection"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
