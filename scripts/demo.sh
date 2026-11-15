#!/usr/bin/env bash
# =============================================================================
# Aegis — AI Operations Intelligence Agent: Interactive Closed-Loop Demo
# =============================================================================
# Demonstrates the complete enterprise incident mitigation lifecycle:
#   DETECT -> CORRELATE -> INVESTIGATE -> ROOT CAUSE -> RECOMMEND ->
#   HUMAN APPROVAL -> CONTROLLED ACTION -> VERIFICATION -> AUDIT
# =============================================================================

set -euo pipefail

AUTO=false
if [[ "${1:-}" == "--auto" ]]; then
    AUTO=true
fi

pause_step() {
    local msg="${1:-Press Enter to advance to next operational phase...}"
    if [ "$AUTO" = false ]; then
        echo ""
        echo -e "\033[33m>>> ${msg}\033[0m"
        read -r
    else
        sleep 1
    fi
}

clear || true
echo -e "\033[36m================================================================================\033[0m"
echo -e "\033[1;37m            AEGIS — PRIVACY-PRESERVING AI OPERATIONS INTELLIGENCE\033[0m"
echo -e "\033[36m                        Interactive Closed-Loop Demo\033[0m"
echo -e "\033[36m================================================================================\033[0m"
echo ""
echo -e "\033[90mGovernance Principle: The AI investigates and recommends,\033[0m"
echo -e "\033[90m                      but only authenticated humans authorize operational changes.\033[0m"
echo ""

# STEP 1
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 1: INGEST TELEMETRY & STATISTICAL ANOMALY DETECTION\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Simulating live telemetry ingestion on microservice mesh..."
echo "    - Service:          checkout-service"
echo "    - Metric:           api_error_rate (HTTP 5xx / total requests)"
echo "    - Nominal Baseline: 0.4% error rate (p95 latency: 110ms)"
echo ""
echo -e "\033[31m[!] INJECTED REGRESSION: Deployment v2.4.1 activated at 14:00:00Z\033[0m"
echo -e "\033[33m[!] TELEMETRY SPIKE DETECTED:\033[0m"
echo -e "    * \033[31mapi_error_rate jumped: 0.4% -> 18.5% (Z-score: +6.2)\033[0m"
echo -e "    * \033[31mlatency_p95 degraded:  110ms -> 820ms\033[0m"
echo -e "    * \033[31mcheckout_failure_rate: 42.8% transaction abandonment\033[0m"
echo -e "    * \033[36mDetector:              ZScoreDetector (severity: HIGH, confidence: 0.95)\033[0m"

pause_step "Advance to Incident Synthesis..."

# STEP 2
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 2: CORRELATION & INCIDENT CANDIDATE SYNTHESIS\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Correlating multi-dimensional anomalies across system boundaries..."
echo "    - Aggregated Anomalies: 31 statistical trips across 4 metric streams"
echo "    - Deduplication Ratio:  100% (synthesized into single incident)"
echo ""
echo -e "\033[31m[+] INCIDENT SYNTHESIZED: INC-101 (SEV-1 CRITICAL)\033[0m"
echo "    * Title:                    Checkout API 500 Error Spike Post-Deployment"
echo "    * Primary Service:          checkout-service"
echo "    * Downstream Systems:       payment-service, inventory-service"
echo -e "    * \033[33mEstimated Revenue Loss:   \$28,500 / hour\033[0m"
echo -e "    * \033[33mCustomer Blast Radius:    450 failed checkout sessions\033[0m"

pause_step "Advance to AI Diagnostic Investigation..."

# STEP 3
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 3: AUTONOMOUS AI INVESTIGATION & ROOT-CAUSE ANALYSIS\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] AI Investigator activated under strict Data Governance Layer..."
echo -e "\033[90m    [Security Boundary] PII redaction & pseudonymization active (Zero DB direct access)\033[0m"
echo ""
echo "[*] AI Tool Invocations:"
echo -e "    -> \033[36mquery_metrics(service='checkout-service', metric='api_error_rate')  => 18.5% spike\033[0m"
echo -e "    -> \033[36mget_deployment_diff(service='checkout-service', v='v2.4.1')         => PR #892 unindexed query\033[0m"
echo -e "    -> \033[36minspect_trace_spans(trace_id='tr-891a', slow_only=true)             => DB connection timeout\033[0m"
echo ""
echo -e "\033[32m[+] DIAGNOSTIC FINDINGS:\033[0m"
echo "    * Root Cause:  Unindexed query in v2.4.1 exhausted Postgres connection pool."
echo -e "    * \033[32mDiagnostic Confidence:  94%  |  Residual Uncertainty:  6%\033[0m"
echo -e "    * \033[36mTime to Diagnose (MTTR): 8.5 seconds\033[0m"

pause_step "Advance to Recommendation & Action Proposal..."

# STEP 4
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 4: STRUCTURED RECOMMENDATION & ACTION PROPOSAL\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Formulating structured corrective mitigation..."
echo "    * Recommendation: Rollback deployment to stable release v2.4.0"
echo -e "    * Priority:       \033[33mP1 - Immediate\033[0m"
echo -e "    * Risk Level:     \033[31mHIGH\033[0m"
echo -e "    * Action Type:    \033[36mROLLBACK_DEPLOYMENT\033[0m"
echo -e "    * Target:         \033[36mcheckout-service\033[0m"
echo ""
echo "[*] Computing Cryptographic Fingerprint over Action Payload..."
FINGERPRINT="a7f3c2e1b9d4085e62f1a308945cf20984ba109f3e498d7520e58f2780e14cb9"
echo -e "    SHA-256 Fingerprint: \033[36m${FINGERPRINT}\033[0m"
echo -e "\033[90m    [Tamper Invariant] Any alteration to service or parameters invalidates hash.\033[0m"

pause_step "Advance to Human Authorization Gate..."

# STEP 5
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 5: HUMAN AUTHORIZATION GATE (GOVERNANCE ENFORCEMENT)\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Testing Invariant 1: Can AI agent self-approve operational changes?"
echo "    -> Actor: Aegis-AI-Investigator (Role: ADMIN)"
echo -e "    \033[31m[BLOCKED - 403 Forbidden] AIApprovalForbiddenError: Autonomous agents cannot approve actions.\033[0m"
echo -e "    \033[32m=> Result: ZERO AUTONOMOUS ADMINISTRATOR INVARIANT PRESERVED.\033[0m"
echo ""
echo "[*] Testing Invariant 2: Authenticated Human Authorization"
echo "    -> Approver:   Alex Chen (On-Call SRE Lead, Role: OPERATOR/ADMIN)"
echo "    -> Reason:     'Rollback approved following connection pool triage.'"
echo "    -> Gate Type:  Typed confirmation required for HIGH-risk actions."
echo -e "    -> Input:      \033[33m'APPROVE ROLLBACK DEPLOYMENT'\033[0m"
echo -e "    \033[32m[+] State Transition: PENDING_APPROVAL -> APPROVED\033[0m"

pause_step "Advance to Action Execution..."

# STEP 6
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 6: CONTROLLED EXECUTION (SIMULATED TOPOLOGY)\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Executing verified operational action..."
echo "    - Execution Mode: STRICT SIMULATION (Zero production blast radius)"
echo -e "    - Fingerprint Match: \033[32mVERIFIED (Original payload intact)\033[0m"
echo ""
echo "    [1/3] Draining ingress connections on checkout-service..."
echo "    [2/3] Switching container active deployment: v2.4.1 -> v2.4.0..."
echo -e "    \033[32m[3/3] Emitted System Event: DEPLOYMENT_STATUS=ROLLED_BACK\033[0m"
echo ""
echo -e "\033[32m[+] State Transition: EXECUTING -> EXECUTED (Duration: 412ms)\033[0m"

pause_step "Advance to Verification..."

# STEP 7
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 7: POST-ACTION TELEMETRY VERIFICATION\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Verification Engine collecting post-mitigation telemetry window..."
echo ""
printf "%-25s %-25s %-25s %s\n" "Metric Indicator" "Pre-Action (Degraded)" "Post-Action (Recovered)" "Status"
echo -e "\033[90m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32m$(printf '%-25s %-25s %-25s %s' 'api_error_rate' '18.5%' '0.42%' 'RECOVERED')\033[0m"
echo -e "\033[32m$(printf '%-25s %-25s %-25s %s' 'latency_p95' '820ms' '118ms' 'RECOVERED')\033[0m"
echo -e "\033[32m$(printf '%-25s %-25s %-25s %s' 'checkout_failure_rate' '42.8%' '0.95%' 'RECOVERED')\033[0m"
echo -e "\033[32m$(printf '%-25s %-25s %-25s %s' 'deployment_version' 'v2.4.1' 'v2.4.0' 'MATCHED')\033[0m"
echo ""
echo -e "\033[32m[+] Resolution Outcome: VERIFIED_SUCCESS\033[0m"
echo -e "    * \033[32mRecovery Score:   98.2% restored to nominal baseline\033[0m"
echo -e "    * \033[32mState Transition: EXECUTED -> VERIFYING -> VERIFIED\033[0m"

pause_step "Advance to Immutable Audit Trail Inspection..."

# STEP 8
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo -e "\033[32mSTEP 8: IMMUTABLE AUDIT TRAIL\033[0m"
echo -e "\033[36m--------------------------------------------------------------------------------\033[0m"
echo "[*] Complete append-only cryptographic provenance record:"
echo ""
printf "%-20s %-22s %-26s %s\n" "Timestamp (UTC)" "Actor" "Action" "Target / Details"
echo -e "\033[90m--------------------------------------------------------------------------------\033[0m"
echo "14:12:00.102Z         aegis-detector         ANOMALY_DETECTED           checkout-service (api_error_rate > 5%)"
echo "14:12:04.450Z         aegis-engine           INCIDENT_CREATED           INC-101 (SEV-1 checkout spike)"
echo "14:12:12.890Z         ai-investigator        INVESTIGATION_COMPLETED    Root cause: DB pool exhaustion"
echo "14:12:14.015Z         ai-investigator        ACTION_PROPOSED            ROLLBACK_DEPLOYMENT (Hash: ${FINGERPRINT:0:16}...)"
echo -e "\033[32m14:12:35.420Z         human:alex_chen        ACTION_APPROVED            Justification: On-Call Lead approved\033[0m"
echo -e "\033[36m14:12:36.100Z         aegis-executor         ACTION_EXECUTED            Rolled back checkout-service to v2.4.0\033[0m"
echo -e "\033[32m14:13:06.500Z         aegis-verifier         ACTION_VERIFIED            Telemetry normalized; 4/4 signals pass\033[0m"
echo ""
echo -e "\033[36m================================================================================\033[0m"
echo -e "\033[1;32m           DEMO COMPLETE: CLOSED OPERATIONAL LOOP VERIFIED 100%\033[0m"
echo -e "\033[36m================================================================================\033[0m"
echo ""
