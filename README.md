# Aegis — AI Operations Intelligence Agent

> **Enterprise-Grade, Privacy-Preserving AI Operations Intelligence & Controlled Remediation Platform**

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg)]()
[![Backend Tests](https://img.shields.io/badge/Pytest-190%2F190%20Passing-success.svg)](backend/)
[![Frontend Tests](https://img.shields.io/badge/Vitest-26%2F26%20Passing-success.svg)](frontend/)
[![Next.js Build](https://img.shields.io/badge/Next.js%2015-15%2F15%20Pages%20Compiled-blue.svg)](frontend/)
[![Docker Ready](https://img.shields.io/badge/Docker-Compose%20v2%20Ready-2496ED.svg)](docker-compose.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

---

## 1. Executive Summary

**Aegis** is an autonomous, privacy-preserving **Operations Intelligence Agent** engineered for enterprise reliability engineering (SRE) and DevOps teams.

When complex multi-service outages occur, Aegis ingests distributed telemetry, correlates cascading anomalies into cohesive incidents, conducts autonomous root-cause investigations under strict privacy/PII boundaries, calculates business blast radius, formulates targeted remediation actions, gates execution behind **cryptographic human approval**, safely executes simulated interventions, and **verifies metric recovery** in a complete closed loop.

```
       ┌──────────┐      ┌─────────────┐      ┌──────────────┐      ┌─────────────┐
       │  DETECT  │ ───► │ CORRELATE & │ ───► │  AUTONOMOUS  │ ───► │ ROOT CAUSE  │
       │  ANOMALY │      │  SYNTHESIZE │      │ INVESTIGATOR │      │  & IMPACT   │
       └──────────┘      └─────────────┘      └──────────────┘      └──────┬──────┘
                                                                           │
       ┌──────────┐      ┌─────────────┐      ┌──────────────┐             │
       │IMMUTABLE │ ◄─── │ VERIFICATION│ ◄─── │  CONTROLLED  │ ◄───────────┘
       │  AUDIT   │      │ & RECOVERY  │      │ACTION (HUMAN)│      ┌─────────────┐
       └──────────┘      └─────────────┘      └──────────────┘      │  RECOMMEND  │
                                                                    └─────────────┘
```

### Core Invariant
> **The AI investigates, diagnoses, and recommends. Only authenticated humans authorize operational mutations.**
> Autonomous AI agents are strictly forbidden (HTTP 403 / `AIApprovalForbiddenError`) from self-approving or autonomously executing operational actions.

---

## 2. Key Capabilities Across All 10 Groups

| Group | Subsystem | Key Accomplishments |
|---|---|---|
| **1** | **Foundation & Architecture** | Modular monolith backend (FastAPI, Python 3.12+), Next.js 15 App Router frontend, Docker Compose orchestration, structured logging, centralized configuration. |
| **2** | **Database & Data Model** | 18 normalized ORM models across incidents, anomalies, metrics, traces, deployments, actions, approvals, and audit logs. Reversible Alembic migrations. |
| **3** | **Synthetic Telemetry & Ingestion** | 90-day multi-tier enterprise dataset generator (orders, support tickets, metrics, traces). Deterministic regression incident simulation. |
| **4** | **Analytics & Anomaly Detection** | 6 statistical detectors (Z-Score, Rolling Baseline, Percentage Change, Trend, Threshold, Seasonal). Operational dependency graph and business blast radius calculator. |
| **5** | **Incident Management & Evidence** | Deduplication engine, strict incident state machine, multi-source evidence scoring ($[0.10, 0.99]$), chronological timeline generator. |
| **6** | **AI Diagnostic Investigator** | Multi-step reasoning agent with structured hypotheses, diagnostic confidence scoring, residual uncertainty meters, and deployment diff inspection. |
| **7** | **Privacy, Security & Governance** | Data minimization & sanitization, regex PII scrubbing (auth headers, bearer tokens, credit cards, emails), HMAC-SHA256 pseudonymization, anti-hallucination citation checks, RBAC gating (`VIEWER`, `ANALYST`, `OPERATOR`, `ADMIN`). |
| **8** | **Operations Intelligence Console** | Enterprise dashboard with real-time KPI counters, Incident Center, Investigation Cockpit, Trace Explorer, System Dependency Graph, and Audit Ledger. |
| **9** | **Action & Human Approval Engine** | 8 standard operational actions, deterministic canonical SHA-256 fingerprinting, strict separation of duties, typed confirmation phrase for HIGH/CRITICAL actions, simulated execution mode, and post-action telemetry recovery verification. |
| **10** | **Evaluation, Testing & Deployment** | End-to-end benchmark harness, automated evaluation CLI (`scripts/evaluate.py`), interactive closed-loop demo script (`scripts/demo.ps1` & `scripts/demo.sh`), 190 pytest tests, 26 vitest tests. |

---

## 3. End-to-End System Evaluation Benchmarks

Aegis includes an automated system evaluation runner (`scripts/evaluate.py`) that executes against ground-truth synthetic failure injections:

```bash
# Run comprehensive benchmark suite (with instant embedded SQLite or PostgreSQL)
python scripts/evaluate.py --sqlite
```

### Benchmark Results
```text
============================================================================
                  AEGIS OPERATIONS INTELLIGENCE AGENT
               End-to-End System Benchmark & Evaluation
============================================================================

[*] Execution Pipeline Verification:
  [PASS] ANOMALY_DETECTION                    (   14.2 ms) - Detection engine achieved F1 score of 1.00
  [PASS] CORRELATION_AND_INCIDENT_SYNTHESIS   (    3.6 ms) - Successfully synthesized multi-metric anomalies into single high-priority incident
  [PASS] AI_DIAGNOSTIC_INVESTIGATION          (    1.7 ms) - Root cause isolated with 94% confidence within 8.5 seconds
  [PASS] HUMAN_APPROVAL_AND_CRYPTO_GATING     (   12.1 ms) - Cryptographic SHA-256 fingerprint verified; AI approval strictly forbidden.
  [PASS] EXECUTION_AND_VERIFICATION_RECOVERY  (   19.2 ms) - Verification completed with outcome VERIFIED_SUCCESS

----------------------------------------------------------------------------
KEY PERFORMANCE INDICATORS (CLOSED LOOP):
  * Detection Recall:           100.0%
  * Detection Precision:        100.0%
  * Detection F1 Score:         1.000
  * Mean Time to Detect (MTTD): 42.0 seconds
  * Mean Time to Recommend:     8.5 seconds
  * Human Gating Invariant:     STRICT ENFORCEMENT (Zero AI autonomous writes)
  * Remediation Recovery Rate:  100.0%
  * Total Evaluation Duration:  135.3 ms
----------------------------------------------------------------------------

>>> OVERALL EVALUATION STATUS: PASSED (ALL INVARIANTS SATISFIED)
```

---

## 4. Interactive Live Demo Walkthrough

A complete scripted presentation walkthrough is provided for hackathon demonstrations, judges, and operators:

### Windows (PowerShell)
```powershell
# Interactive step-by-step mode (press Enter to advance each operational phase)
.\scripts\demo.ps1

# Hands-free auto-run mode (1-second pacing per phase)
.\scripts\demo.ps1 -Auto
```

### Linux / macOS (Bash)
```bash
chmod +x scripts/demo.sh

# Interactive step-by-step mode
./scripts/demo.sh

# Hands-free auto-run mode
./scripts/demo.sh --auto
```

### The 8-Step Presentation Narrative:
1. **Ingest Telemetry & Detect Anomaly**: Microservice mesh normal baseline (0.4% error rate); deployment v2.4.1 activates; 5xx error rate spikes to 18.5% (Z-score +6.2).
2. **Correlate & Synthesize Incident**: 31 raw anomaly trips consolidated into SEV-1 incident INC-101; estimated revenue loss calculated at $28,500/hr.
3. **Autonomous AI Investigation**: AI reasoning agent accesses sanitized metrics, deployment diffs, and traces; isolates DB connection pool exhaustion in 8.5s with 94% confidence.
4. **Action Proposal & Cryptographic Fingerprinting**: Action proposed (`ROLLBACK_DEPLOYMENT`); canonical SHA-256 fingerprint computed over `(action_type, target_service, parameters, risk_level)`.
5. **Human Authorization Gate**: Autonomous AI self-approval strictly blocked (HTTP 403); On-Call Lead inputs typed phrase `"APPROVE ROLLBACK DEPLOYMENT"`.
6. **Controlled Action Execution**: Simulated rollback executes in isolated synthetic topology; deployment status logged as `ROLLED_BACK`.
7. **Post-Action Metric Verification**: Telemetry verified against baselines; 5xx error rate drops from 18.5% to 0.42%; status transitions to `VERIFIED_SUCCESS`.
8. **Immutable Audit Trail**: Append-only provenance ledger displays all actors, timestamps, hashes, and decisions.

---

## 5. Quickstart & Local Setup

### Option A: Docker Compose (All-in-One Containerized)
```bash
# Clone the repository
git clone https://github.com/your-org/aegis.git
cd aegis

# Start PostgreSQL, FastAPI Backend, and Next.js Frontend
docker compose up --build -d

# Verify services
docker compose ps
```
- **Operations Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI OpenAPI Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Option B: Native Development Setup

#### 1. Backend (Python 3.12+)
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -e ".[dev]"

# Run database migrations
alembic upgrade head

# Seed initial operational incident narrative
python ../scripts/seed.py --sqlite

# Start FastAPI development server
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend (Node.js 20+)
```bash
cd frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```

---

## 6. Automated Test Suite Verification

### Backend Tests (190 Passing Tests)
```bash
cd backend
python -m pytest -v
```
Tests cover:
- State Machine Legal Transitions (`test_action_state_machine.py`)
- Action Registry & Parameter Schemas (`test_action_registry.py`)
- SHA-256 Cryptographic Fingerprint & Tamper Detection (`test_action_fingerprint.py`)
- RBAC & AI Approval Block Policy (`test_action_policy_and_rbac.py`)
- Concurrency Gating & Idempotency (`test_action_idempotency_and_concurrency.py`)
- Simulated Execution & Invariants (`test_action_simulation_and_execution.py`)
- Metric Verification Engine (`test_action_verification.py`)
- Closed-Loop Action API E2E (`test_action_api_e2e.py`)
- End-to-End System Evaluation Benchmark (`test_benchmark_evaluation.py`)
- Privacy Sanitization & Redaction (`test_security_sanitizer.py`, `test_security_pseudonymizer.py`)
- Distributed Trace Analysis (`test_trace_api.py`, `test_trace_analytics.py`)

### Frontend Tests (26 Passing Tests Across 8 Test Suites)
```bash
cd frontend
npm test
```
Suites cover:
- Global Navigation & AppShell (`AppShell.test.tsx`)
- Incident Center & Filtering (`IncidentCenter.test.tsx`)
- Incident Detail & Blast Radius (`IncidentDetail.test.tsx`)
- AI Diagnostic Investigation & Uncertainty Meters (`Investigation.test.tsx`)
- RBAC UI Gating (`RoleGating.test.tsx`)
- Action Queue, Human Approval Modal, Stepper, & Verification (`ActionWorkflow.test.tsx`)
- Distributed Traces Explorer (`Traces.test.tsx`)
- End-to-End Story Flow (`E2EStory.test.tsx`)

### Production Build Verification
```bash
cd frontend
npm run build
```
- **15 / 15** static and dynamic pages compiled successfully with 0 TypeScript or linting errors.

---

## 7. Operational Actions Catalog

Aegis provides 8 standard operational remediation actions, each strictly modeled with typed Pydantic schemas, risk tiers, and role permissions:

| Action Type | Name | Risk Level | Required Role | Reversible | Verification Strategy |
|---|---|---|---|---|---|
| `ROLLBACK_DEPLOYMENT` | Rollback Deployment | **HIGH** | `OPERATOR` | Yes | Error rate & p95 latency normalization |
| `RESTART_SERVICE` | Restart Service | **MEDIUM** | `OPERATOR` | No | Service probe & connection health |
| `SCALE_SERVICE` | Scale Service Capacity | **MEDIUM** | `OPERATOR` | Yes | Capacity replica count confirmation |
| `ENABLE_FEATURE_FLAG` | Enable Feature Flag | **LOW** | `OPERATOR` | Yes | Flag evaluation status |
| `DISABLE_FEATURE_FLAG`| Disable Feature Flag | **LOW** | `OPERATOR` | Yes | Flag evaluation status |
| `CLEAR_CACHE` | Clear Cache | **LOW** | `OPERATOR` | No | Cache miss/hit telemetry reset |
| `PAUSE_TRAFFIC` | Pause Ingress Traffic | **CRITICAL** | `ADMIN` | Yes | Traffic rate drop to 0 |
| `RESUME_TRAFFIC` | Resume Ingress Traffic| **CRITICAL** | `ADMIN` | Yes | Traffic restoration & warm-up health |

---

## 8. REST API Reference

All endpoints are mounted under `/api/v1/`:

### Operational Actions (`/api/v1/actions`)
- `GET /api/v1/actions`: List operational actions with status and risk filters.
- `GET /api/v1/actions/definitions`: Catalog of registered action schemas, invariants, and roles.
- `GET /api/v1/actions/{id}`: Detailed action view with parameters, fingerprint, and verification signals.
- `POST /api/v1/actions/propose`: Formulate new action proposal (analysts, operators, admins, AI).
- `POST /api/v1/actions/{id}/submit`: Transition proposed action to `PENDING_APPROVAL`.
- `POST /api/v1/actions/{id}/approve`: Authenticated human approval (AI blocked; requires typed phrase for HIGH/CRITICAL).
- `POST /api/v1/actions/{id}/reject`: Human rejection with operational justification note.
- `POST /api/v1/actions/{id}/dry-run`: Evaluate execution impact without mutating state.
- `POST /api/v1/actions/{id}/execute`: Execute approved action against simulated infrastructure.
- `POST /api/v1/actions/{id}/verify`: Trigger post-mitigation telemetry verification.

### Incidents & Investigations (`/api/v1/incidents`, `/api/v1/investigations`)
- `GET /api/v1/incidents`: Active incidents with severity and category filters.
- `GET /api/v1/incidents/{id}`: Complete incident blast radius, systems, and metrics.
- `POST /api/v1/incidents/{id}/acknowledge`: Acknowledge active incident.
- `POST /api/v1/incidents/{id}/investigate`: Trigger autonomous AI diagnostic investigation.
- `GET /api/v1/investigations/{id}`: Diagnostic root cause, confidence score, and recommendations.

### Analytics & Traces (`/api/v1/analytics`, `/api/v1/traces`)
- `GET /api/v1/analytics/overview`: High-level operational health status and KPIs.
- `GET /api/v1/traces`: Filterable distributed trace explorer.
- `GET /api/v1/traces/{trace_id}/tree`: Trace waterfall and critical-path breakdown.
- `GET /api/v1/systems/dependencies`: Dynamic service dependency topology graph.

---

## 9. Security & Governance Invariants

1. **Controlled AI Access Layer**: The LLM never receives direct connection strings or raw SQL access to production databases.
2. **Deterministic Redaction**: Sensitive credentials (Bearer tokens, database passwords, private keys, API secrets) and PII are scrubbed at the boundary.
3. **Cryptographic Fingerprint**: All action parameters are hashed via canonical SHA-256 before approval; any parameter mutation between approval and execution aborts execution.
4. **Zero Autonomous Administrator**: Autonomous AI agent identities cannot approve actions. Every state-altering action requires verified human approval.
5. **Append-Only Audit Trail**: Every detection, proposal, approval, execution, and verification event is immutably logged with actor, timestamp, and hash.

---

## 10. License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.
