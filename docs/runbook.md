# Aegis Operator Runbook

> **Standard Operating Procedures (SOP) for On-Call SREs, Incident Commanders, and System Administrators.**

---

## 1. System Overview

Aegis is an operations intelligence and remediation platform operating under the **human-in-the-loop governance model**:
$$\text{DETECT} \to \text{INVESTIGATE} \to \text{ROOT CAUSE} \to \text{RECOMMEND} \to \mathbf{HUMAN\ APPROVAL} \to \mathbf{ACTION} \to \mathbf{VERIFICATION} \to \mathbf{AUDIT}$$

**Core Operating Principle**: The AI investigates, formulates hypotheses, isolates root causes, and recommends actions. **Only authenticated humans can authorize operational state mutations.**

---

## 2. Operator Roles & Permissions

Aegis enforces strict Role-Based Access Control (RBAC):

| Role | Permissions |
|---|---|
| `VIEWER` | Read-only access to overview dashboards, trace explorer, dependency graphs, and audit logs. |
| `ANALYST` | Viewer permissions plus triggering AI investigations and adding operator investigation notes. |
| `OPERATOR`| Full operational triage: acknowledge incidents, trigger investigations, formulate action proposals, and approve `LOW` and `MEDIUM` risk actions. |
| `ADMIN` | Complete authority: approve `HIGH` and `CRITICAL` risk actions (e.g. `PAUSE_TRAFFIC`), adjust governance policy, and override system locks. |

---

## 3. Incident Triage Workflow

### Step 1: Monitor Overview Dashboard
- Navigate to `/dashboard` to review active KPIs:
  - Active Incidents (SEV-1 through SEV-4)
  - Anomaly detection rates across operational metrics
  - Total estimated revenue blast radius
  - Distributed trace error & slow request rates

### Step 2: Review Synthesized Incidents
- Navigate to `/incidents` or click on an active incident banner.
- Verify the **Business Blast Radius**:
  - Estimated hourly financial loss
  - Count of affected customer sessions
  - Affected microservice dependencies
- Click **Acknowledge Incident** to take ownership.

### Step 3: Trigger AI Diagnostic Investigation
- From the Incident Detail page (`/incidents/[id]`), click **Trigger AI Investigation**.
- The AI Investigator will autonomously execute typed read-only tools:
  - Query operational metrics
  - Retrieve deployment diffs and git commits
  - Inspect distributed trace waterfalls and critical paths
  - Check service health probes
- Review the generated **Diagnostic Findings**:
  - Identified Root Cause
  - Diagnostic Confidence meter (e.g. 94%)
  - Residual Uncertainty meter (e.g. 6%)
  - Evidence citations (validating database record provenance)

---

## 4. Action Review & Human Approval Workflow

### Step 1: Inspect the Action Proposal
- From the Investigation page or `/actions`, select the pending action proposal.
- Verify the following parameters:
  - **Action Type**: (e.g. `ROLLBACK_DEPLOYMENT`, `RESTART_SERVICE`, `SCALE_SERVICE`)
  - **Target Service**: (e.g. `checkout-service`)
  - **Parameters**: Confirm specific target versions, replica counts, or flag keys.
  - **Risk Tier**: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.
  - **Cryptographic Fingerprint**: Review the SHA-256 fingerprint generated over the canonical action payload.

### Step 2: Authorize or Reject Action
- If the action is **HIGH** or **CRITICAL** risk:
  - You must type the exact confirmation phrase shown in the gate (e.g. `APPROVE ROLLBACK DEPLOYMENT`).
  - Provide a clear operational justification note (e.g. *"Approved by On-Call Lead following database pool exhaustion triage"*).
  - Click **Grant Human Authorization**.
- If the action proposal is not appropriate:
  - Click **Reject Proposal**.
  - Provide a mandatory rejection explanation note for the immutable audit ledger.

---

## 5. Controlled Execution & Verification

### Step 1: Optional Dry-Run
- Before executing, toggle **Dry Run** to simulate the execution without applying actual state mutations.
- Review simulated state transitions and potential downstream warnings.

### Step 2: Execute Action
- Click **Execute Action**.
- In standard mode, the action executes against the simulated infrastructure topology (`ACTION_EXECUTION_MODE=SIMULATED`), avoiding external cloud blast radius.
- The action progresses through: `APPROVED` $\to$ `EXECUTING` $\to$ `EXECUTED`.

### Step 3: Telemetry Verification
- Click **Run Telemetry Verification** (or observe automated verification).
- The Verification Engine evaluates post-execution metric recovery windows:
  - Compares pre-mitigation degraded metrics vs post-mitigation recovery metrics.
  - Checks specific threshold invariants (e.g. error rate $\le 2\%$, latency $\le 300\text{ms}$).
- When all signals pass, the action transitions to `VERIFIED_SUCCESS`.

---

## 6. Audit & Compliance Inspection

- Navigate to `/audit` to inspect the append-only audit trail:
  - Every anomaly detection event
  - Incident creation and severity escalation
  - AI tool invocations and findings
  - Human approval decisions and justification notes
  - Action execution results and duration
  - Verification recovery outcomes
- All records include immutable timestamps, actor IDs, request IDs, and cryptographic hashes.

---

## 7. Emergency & CLI Operations

### Run Automated System Evaluation Benchmark
```bash
# Verify all closed-loop operational invariants
python scripts/evaluate.py --sqlite
```

### Run Closed-Loop Presentation Demo
```powershell
# Interactive walkthrough
.\scripts\demo.ps1
```

### Reset & Seed Initial Demo Data
```bash
python scripts/seed.py --sqlite
```
