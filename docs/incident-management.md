# Aegis Incident Management, Correlation & Evidence Subsystem

## Overview

The **Incident Management Subsystem** (`app/incidents`) converts raw statistical anomaly clusters (`IncidentCandidate`) and manual operator declarations into structured, explainable, auditable operational incidents. It establishes an immutable single source of truth for all operational disruptions, ensuring deterministic severity determination, strict lifecycle transitions, blast radius tracking, multi-source evidence management, chronological timeline reconstruction, and append-only audit logging.

```
                              INCIDENT MANAGEMENT SUBSYSTEM
                              
   +-----------------------+     +------------------------+
   |  Incident Candidate   |     |  Manual Operator Input |
   |  (Group 4 Analytics)  |     |  (REST API Endpoint)   |
   +-----------+-----------+     +-----------+------------+
               \                             /
                \                           /
                 v                         v
   +------------------------------------------------------+
   |             IncidentCreationService                  |
   |  - Deterministic 4-hour temporal SHA-256 fingerprint |
   |  - Deduplication via active incident evaluation      |
   |  - Autonomous category & affected system inference   |
   |  - Initial non-causal title and summary framing     |
   |  - Primary evidence ingestion                        |
   +---------------------------+--------------------------+
                               |
                               v
   +------------------------------------------------------+
   |             IncidentSeverityService                  |
   |  - Multi-tier deterministic severity evaluation     |
   |  - Monotonic escalation (never auto down-scales)    |
   +---------------------------+--------------------------+
                               |
                               v
   +------------------------------------------------------+
   |             IncidentLifecycleManager                 |
   |  - Strict State Machine:                             |
   |    OPEN -> INVESTIGATING -> MITIGATED -> RESOLVED -> |
   |    CLOSED (terminal)                                 |
   |  - Explicit operator acknowledgement tracking        |
   |  - Mandatory resolution summary & authorization      |
   +---------------------------+--------------------------+
                               |
                               v
   +------------------------------------------------------+
   |             IncidentEvidenceService                  |
   |  - 8 Evidence Types (Deployments, Events, etc.)      |
   |  - Relevance scoring [0.10, 0.99]                    |
   |  - Deduplication on (incident_id, type, source_id)   |
   +---------------------------+--------------------------+
                               |
                               v
   +------------------------------------------------------+
   |             IncidentTimelineService                  |
   |  - Chronological multi-source event aggregation      |
   |  - Automatic PII scrubbing (emails, phones masked)   |
   |  - Non-causal neutral timing descriptions            |
   +---------------------------+--------------------------+
                               |
                               v
   +------------------------------------------------------+
   |             IncidentAuditRecorder                    |
   |  - Append-only sanitized audit trail                 |
   |  - Token/credential scrubbing                        |
   +------------------------------------------------------+
```

---

## 1. Incident Creation & Deterministic Deduplication

### 1.1 Candidate Transformation
When an `IncidentCandidate` is ingested:
* **Fingerprint Generation**: SHA-256 hash over `(company_id, sorted(affected_metrics), 4-hour temporal bucket)`.
* **Deduplication Check**: Queries `incidents` for active (non-closed) records with the identical fingerprint.
  * If found: Merges any newly observed anomalies into the existing incident, updates preliminary impact if increased, and returns HTTP 200 without creating a redundant duplicate.
  * If new: Constructs an `Incident` entity, associates all candidate anomalies, derives affected subsystems, and sets initial status to `OPEN`.

### 1.2 Non-Causal Deterministic Framing
Aegis strictly avoids asserting unverified root causes prior to formal AI investigation. Generated titles and summaries strictly describe observed telemetry:
* *Correct*: `"Degradation observed across checkout_failure_rate, api_error_rate. Deployment v4.8.2 completed shortly before observed degradation."`
* *Incorrect*: `"Deployment v4.8.2 broke the checkout service."`

---

## 2. Monotonic Severity & Escalation

### 2.1 Deterministic Severity Evaluation
Severity is calculated through rule-based criteria:
* **CRITICAL**: Critical anomaly detected on primary SLA metric (e.g. `checkout_failure_rate`), OR high anomaly with $\ge 3$ degraded metrics, OR estimated revenue impact $\ge \$10,000$.
* **HIGH**: High anomaly detected, OR $\ge 2$ correlated metrics degraded, OR estimated revenue impact $\ge \$2,500$.
* **MEDIUM**: Medium anomaly detected, OR isolated metric degradation.
* **LOW**: Informational or minor operational drift.

### 2.2 Monotonicity Rule
To protect operational awareness, **severity only escalates upward**. If a critical evidence item arrives or business impact jumps, severity escalates (e.g. `MEDIUM` $\to$ `CRITICAL`). Metric recovery does **not** automatically downgrade incident severity; incident recovery is modeled through lifecycle status (`MITIGATED` / `RESOLVED`), preserving historical severity severity tiering.

---

## 3. Incident Lifecycle State Machine

The incident state machine enforces strict operational governance:

```
[OPEN] ---> [INVESTIGATING] ---> [MITIGATED] ---> [RESOLVED] ---> [CLOSED] (terminal)
  |                 ^                 |               |
  |                 |                 |               |
  +-----------------+-----------------+               |
  |                                                   |
  +---------------------------------------------------+
```

### 3.1 Lifecycle Rules
1. **`OPEN -> INVESTIGATING`**: Commences triage; automatically timestamps `investigation_started_at`.
2. **`INVESTIGATING -> MITIGATED`**: Mitigation executed (e.g., traffic shedding, feature flag disabled); timestamps `mitigated_at`.
3. **`MITIGATED -> RESOLVED`**: Requires mandatory `resolution_summary` and `resolved_by`. Attempts to resolve without a summary are rejected with HTTP 400. Timestamps `resolved_at`.
4. **`RESOLVED -> CLOSED`**: Requires `closed_by`. Timestamps `closed_at`.
5. **`CLOSED -> *`**: **Terminal State**. Closed incidents cannot be reopened. New operational degradation creates a new incident.

### 3.2 Human Acknowledgement
* Operators acknowledge incidents via `POST /api/v1/incidents/{id}/acknowledge`.
* Records `acknowledged_at` timestamp, `acknowledged_by` operator username, and emits an `INCIDENT_ACKNOWLEDGED` audit log.
* Can optionally transition status directly to `INVESTIGATING`.

---

## 4. Multi-Source Evidence Management

Aegis models evidence as first-class entities (`IncidentEvidence`) linked to an incident:

### 4.1 Supported Evidence Source Types
* `ANOMALY`: Direct statistical anomaly observation.
* `DEPLOYMENT`: Service release, code deployment, or infrastructure configuration change.
* `SYSTEM_EVENT`: Infrastructure log event, error cascade, connection exhaustion.
* `METRIC`: Raw telemetry time-series observation.
* `SUPPORT_TICKET`: Inbound customer assistance ticket.
* `CUSTOMER_COMPLAINT`: Customer sentiment and operational feedback report.
* `DOCUMENT`: Runbook, architectural specification, or post-mortem documentation.
* `MANUAL_NOTE`: Operator annotation or triage note.

### 4.2 Deterministic Relevance Scoring
Relevance scores are bounded in $[0.10, 0.99]$:
$$\text{Score} = \min(0.99, \max(0.10, \text{BaseScore} \times \text{TimeDecay} + \text{SeverityBonus} + \text{DirectMetricBonus}))$$
* **Base Weight**: Anomaly (0.90), Deployment (0.88), System Event (0.85), Complaint (0.80), Support Ticket (0.75), Metric (0.75), Note (0.70), Document (0.60).
* **Temporal Proximity**: $\le 30$ mins ($1.0\times$), $\le 2$ hours ($0.92\times$), $\le 6$ hours ($0.82\times$), $> 6$ hours (linear decay).
* **Severity Bonus**: Critical ($+0.08$), High ($+0.04$).
* **Direct Metric Bonus**: $+0.05$ if directly referencing an affected metric.

### 4.3 Evidence Deduplication
Prevents attaching duplicate records by querying `(incident_id, source_type, source_id)`.

---

## 5. Chronological Multi-Source Timeline Engine

The timeline engine (`IncidentTimelineService.build_timeline`) aggregates heterogeneous operational data:
1. Incident creation and lifecycle milestones (`INCIDENT_CREATED`, `ACKNOWLEDGED`, `STATUS_CHANGED`).
2. Attached evidence records (`EVIDENCE_ADDED`).
3. Operator annotations (`NOTE_ADDED`).
4. Correlated anomalies (`ANOMALY_DETECTED`).
5. Temporally adjacent deployments, system events, support tickets, and complaints within $[t_{detected} - 2\text{hr}, t_{resolved} + 1\text{hr}]$.

### 5.1 Privacy Preservation & PII Masking
All customer feedback summaries and operator notes pass through privacy scrubbers before inclusion in timeline views:
* Email addresses $\to$ `[REDACTED EMAIL]`
* Phone numbers $\to$ `[REDACTED PHONE]`
* Customer identifiers abstracted into aggregate counts.

---

## 6. Business Impact Estimation & Delta Tracking

* **Explicit "Preliminary" Semantics**: Impact estimates are flagged with `is_preliminary: true` to indicate automated approximation rather than audited accounting figures.
* **Impact Delta Engine**: Tracks successive revisions (`revenue_delta`, `orders_delta`, `users_delta`, `support_delta`).
* **History Audit**: All revisions appended to `incident_metadata["impact_history"]` and recorded in immutable audit logs.

---

## 7. REST API Reference

| Method | Endpoint | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/incidents` | List incidents with filters & safe sorting | 200 |
| `POST` | `/api/v1/incidents` | Manually declare an operational incident | 201 |
| `POST` | `/api/v1/incidents/from-candidate` | Create or deduplicate incident from candidate | 201 (new), 200 (merged) |
| `GET` | `/api/v1/incidents/{id}` | Get incident detail (anomalies, evidence, notes) | 200, 404 |
| `POST` | `/api/v1/incidents/{id}/status` | Transition lifecycle status | 200, 400, 404 |
| `POST` | `/api/v1/incidents/{id}/acknowledge` | Record operator acknowledgement | 200, 404 |
| `GET` | `/api/v1/incidents/{id}/timeline` | Retrieve chronological multi-source timeline | 200, 404 |
| `GET` | `/api/v1/incidents/{id}/evidence` | List attached evidence items | 200, 404 |
| `POST` | `/api/v1/incidents/{id}/evidence` | Attach new evidence item | 201, 404 |
| `GET` | `/api/v1/incidents/{id}/notes` | List operator notes | 200, 404 |
| `POST` | `/api/v1/incidents/{id}/notes` | Append operator note | 201, 404 |
| `POST` | `/api/v1/incidents/{id}/impact` | Update blast radius estimation & record delta | 200, 404 |
| `GET` | `/api/v1/incidents/{id}/correlation` | Get high-level correlation overview | 200, 404 |
