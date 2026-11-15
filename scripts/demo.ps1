# =============================================================================
# Aegis -- AI Operations Intelligence Agent: Interactive Closed-Loop Demo
# =============================================================================
# Demonstrates the complete enterprise incident mitigation lifecycle:
#   DETECT -> CORRELATE -> INVESTIGATE -> ROOT CAUSE -> RECOMMEND ->
#   HUMAN APPROVAL -> CONTROLLED ACTION -> VERIFICATION -> AUDIT
# =============================================================================

param (
    [switch]$Auto = $false
)

$ErrorActionPreference = "Stop"

function Pause-Step {
    param([string]$Message = "Press Enter to advance to next operational phase...")
    if (-not $Auto) {
        Write-Host ""
        Write-Host ">>> $Message" -ForegroundColor Yellow
        [void][System.Console]::ReadLine()
    } else {
        Start-Sleep -Seconds 1
    }
}

Clear-Host
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "            AEGIS -- PRIVACY-PRESERVING AI OPERATIONS INTELLIGENCE" -ForegroundColor White
Write-Host "                        Interactive Closed-Loop Demo" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Governance Principle: The AI investigates and recommends," -ForegroundColor DarkGray
Write-Host "                      but only authenticated humans authorize operational changes." -ForegroundColor DarkGray
Write-Host ""

# -----------------------------------------------------------------------------
# STEP 1: Telemetry Stream & Anomaly Detection
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 1: INGEST TELEMETRY AND STATISTICAL ANOMALY DETECTION" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Simulating live telemetry ingestion on microservice mesh..." -ForegroundColor White
Write-Host "    - Service:          checkout-service" -ForegroundColor Gray
Write-Host "    - Metric:           api_error_rate (HTTP 5xx / total requests)" -ForegroundColor Gray
Write-Host "    - Nominal Baseline: 0.4% error rate (p95 latency: 110ms)" -ForegroundColor Gray
Write-Host ""
Write-Host "[!] INJECTED REGRESSION: Deployment v2.4.1 activated at 14:00:00Z" -ForegroundColor Red
Write-Host "[!] TELEMETRY SPIKE DETECTED:" -ForegroundColor Yellow
Write-Host "    * api_error_rate jumped: 0.4% -> 18.5% (Z-score: +6.2)" -ForegroundColor Red
Write-Host "    * latency_p95 degraded:  110ms -> 820ms" -ForegroundColor Red
Write-Host "    * checkout_failure_rate: 42.8% transaction abandonment" -ForegroundColor Red
Write-Host "    * Detector:              ZScoreDetector (severity: HIGH, confidence: 0.95)" -ForegroundColor Cyan

Pause-Step "Advance to Incident Synthesis..."

# -----------------------------------------------------------------------------
# STEP 2: Incident Correlation & Blast Radius Calculation
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 2: CORRELATION AND INCIDENT CANDIDATE SYNTHESIS" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Correlating multi-dimensional anomalies across system boundaries..." -ForegroundColor White
Write-Host "    - Aggregated Anomalies: 31 statistical trips across 4 metric streams" -ForegroundColor Gray
Write-Host "    - Deduplication Ratio:  100% (synthesized into single incident)" -ForegroundColor Gray
Write-Host ""
Write-Host "[+] INCIDENT SYNTHESIZED: INC-101 (SEV-1 CRITICAL)" -ForegroundColor Red
Write-Host "    * Title:                    Checkout API 500 Error Spike Post-Deployment" -ForegroundColor White
Write-Host "    * Primary Service:          checkout-service" -ForegroundColor White
Write-Host "    * Downstream Systems:       payment-service, inventory-service" -ForegroundColor White
Write-Host "    * Estimated Revenue Loss:   `$28,500 / hour" -ForegroundColor Yellow
Write-Host "    * Customer Blast Radius:    450 failed checkout sessions" -ForegroundColor Yellow

Pause-Step "Advance to AI Diagnostic Investigation..."

# -----------------------------------------------------------------------------
# STEP 3: Autonomous AI Investigation & Evidence Retrieval
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 3: AUTONOMOUS AI INVESTIGATION AND ROOT-CAUSE ANALYSIS" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] AI Investigator activated under strict Data Governance Layer..." -ForegroundColor White
Write-Host "    [Security Boundary] PII redaction and pseudonymization active (Zero DB direct access)" -ForegroundColor DarkGray
Write-Host ""
Write-Host "[*] AI Tool Invocations:" -ForegroundColor White
Write-Host "    -> query_metrics: api_error_rate => 18.5% spike" -ForegroundColor Cyan
Write-Host "    -> get_deployment_diff: checkout-service v2.4.1 => PR #892 unindexed query" -ForegroundColor Cyan
Write-Host "    -> inspect_trace_spans: trace_id tr-891a => DB connection timeout" -ForegroundColor Cyan
Write-Host ""
Write-Host "[+] DIAGNOSTIC FINDINGS:" -ForegroundColor Green
Write-Host "    * Root Cause:  Unindexed query in v2.4.1 exhausted Postgres connection pool." -ForegroundColor White
Write-Host "    * Diagnostic Confidence:  94%  |  Residual Uncertainty:  6%" -ForegroundColor Green
Write-Host "    * Time to Diagnose (MTTR): 8.5 seconds" -ForegroundColor Cyan

Pause-Step "Advance to Recommendation and Action Proposal..."

# -----------------------------------------------------------------------------
# STEP 4: Recommendation Formulation & Action Proposal
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 4: STRUCTURED RECOMMENDATION AND ACTION PROPOSAL" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Formulating structured corrective mitigation..." -ForegroundColor White
Write-Host "    * Recommendation: Rollback deployment to stable release v2.4.0" -ForegroundColor White
Write-Host "    * Priority:       P1 - Immediate" -ForegroundColor Yellow
Write-Host "    * Risk Level:     HIGH" -ForegroundColor Red
Write-Host "    * Action Type:    ROLLBACK_DEPLOYMENT" -ForegroundColor Cyan
Write-Host "    * Target:         checkout-service" -ForegroundColor Cyan
Write-Host ""
Write-Host "[*] Computing Cryptographic Fingerprint over Action Payload..." -ForegroundColor White
$sampleFingerprint = "a7f3c2e1b9d4085e62f1a308945cf20984ba109f3e498d7520e58f2780e14cb9"
Write-Host "    SHA-256 Fingerprint: $sampleFingerprint" -ForegroundColor Cyan
Write-Host "    [Tamper Invariant] Any alteration to service or parameters invalidates hash." -ForegroundColor DarkGray

Pause-Step "Advance to Human Authorization Gate..."

# -----------------------------------------------------------------------------
# STEP 5: Human Authorization Gate & RBAC Verification
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 5: HUMAN AUTHORIZATION GATE (GOVERNANCE ENFORCEMENT)" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Testing Invariant 1: Can AI agent self-approve operational changes?" -ForegroundColor White
Write-Host "    -> Actor: Aegis-AI-Investigator (Role: ADMIN)" -ForegroundColor DarkGray
Write-Host "    [BLOCKED - 403 Forbidden] AIApprovalForbiddenError: Autonomous agents cannot approve actions." -ForegroundColor Red
Write-Host "    => Result: ZERO AUTONOMOUS ADMINISTRATOR INVARIANT PRESERVED." -ForegroundColor Green
Write-Host ""
Write-Host "[*] Testing Invariant 2: Authenticated Human Authorization" -ForegroundColor White
Write-Host "    -> Approver:   Alex Chen (On-Call SRE Lead, Role: OPERATOR/ADMIN)" -ForegroundColor White
Write-Host "    -> Reason:     'Rollback approved following connection pool triage.'" -ForegroundColor White
Write-Host "    -> Gate Type:  Typed confirmation required for HIGH-risk actions." -ForegroundColor White
Write-Host "    -> Input:      'APPROVE ROLLBACK DEPLOYMENT'" -ForegroundColor Yellow
Write-Host "    [+] State Transition: PENDING_APPROVAL -> APPROVED" -ForegroundColor Green

Pause-Step "Advance to Action Execution..."

# -----------------------------------------------------------------------------
# STEP 6: Controlled Action Execution (Simulation Mode)
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 6: CONTROLLED EXECUTION (SIMULATED TOPOLOGY)" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Executing verified operational action..." -ForegroundColor White
Write-Host "    - Execution Mode: STRICT SIMULATION (Zero production blast radius)" -ForegroundColor Gray
Write-Host "    - Fingerprint Match: VERIFIED (Original payload intact)" -ForegroundColor Green
Write-Host ""
Write-Host "    [1/3] Draining ingress connections on checkout-service..." -ForegroundColor Gray
Write-Host "    [2/3] Switching container active deployment: v2.4.1 -> v2.4.0..." -ForegroundColor Gray
Write-Host "    [3/3] Emitted System Event: DEPLOYMENT_STATUS=ROLLED_BACK" -ForegroundColor Green
Write-Host ""
Write-Host "[+] State Transition: EXECUTING -> EXECUTED (Duration: 412ms)" -ForegroundColor Green

Pause-Step "Advance to Verification..."

# -----------------------------------------------------------------------------
# STEP 7: Post-Action Verification & Metric Recovery
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 7: POST-ACTION TELEMETRY VERIFICATION" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Verification Engine collecting post-mitigation telemetry window..." -ForegroundColor White
Write-Host ""
Write-Host "Metric Indicator          Pre-Action (Degraded)    Post-Action (Recovered)    Status" -ForegroundColor Gray
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "api_error_rate            18.5%                    0.42%                      RECOVERED" -ForegroundColor Green
Write-Host "latency_p95               820ms                    118ms                      RECOVERED" -ForegroundColor Green
Write-Host "checkout_failure_rate     42.8%                    0.95%                      RECOVERED" -ForegroundColor Green
Write-Host "deployment_version        v2.4.1                   v2.4.0                     MATCHED" -ForegroundColor Green
Write-Host ""
Write-Host "[+] Resolution Outcome: VERIFIED_SUCCESS" -ForegroundColor Green
Write-Host "    * Recovery Score:   98.2% restored to nominal baseline" -ForegroundColor Green
Write-Host "    * State Transition: EXECUTED -> VERIFYING -> VERIFIED" -ForegroundColor Green

Pause-Step "Advance to Immutable Audit Trail Inspection..."

# -----------------------------------------------------------------------------
# STEP 8: Immutable Audit Trail Inspection
# -----------------------------------------------------------------------------
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "STEP 8: IMMUTABLE AUDIT TRAIL" -ForegroundColor Green
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkCyan
Write-Host "[*] Complete append-only cryptographic provenance record:" -ForegroundColor White
Write-Host ""
Write-Host "Timestamp (UTC)       Actor                  Action                     Target / Details" -ForegroundColor Gray
Write-Host "--------------------------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "14:12:00.102Z         aegis-detector         ANOMALY_DETECTED           checkout-service (api_error_rate > 5%)" -ForegroundColor White
Write-Host "14:12:04.450Z         aegis-engine           INCIDENT_CREATED           INC-101 (SEV-1 checkout spike)" -ForegroundColor White
Write-Host "14:12:12.890Z         ai-investigator        INVESTIGATION_COMPLETED    Root cause: DB pool exhaustion" -ForegroundColor White
Write-Host "14:12:14.015Z         ai-investigator        ACTION_PROPOSED            ROLLBACK_DEPLOYMENT (Hash: a7f3c2e1b9d4085e...)" -ForegroundColor White
Write-Host "14:12:35.420Z         human:alex_chen        ACTION_APPROVED            Justification: On-Call Lead approved" -ForegroundColor Green
Write-Host "14:12:36.100Z         aegis-executor         ACTION_EXECUTED            Rolled back checkout-service to v2.4.0" -ForegroundColor Cyan
Write-Host "14:13:06.500Z         aegis-verifier         ACTION_VERIFIED            Telemetry normalized; 4/4 signals pass" -ForegroundColor Green
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "           DEMO COMPLETE: CLOSED OPERATIONAL LOOP VERIFIED 100%" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
