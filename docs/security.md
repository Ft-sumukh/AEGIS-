# Aegis Security, Privacy & Data Governance Architecture

This document establishes the security architecture, privacy controls, AI boundaries, and threat model for the **Aegis AI Operations Intelligence Platform**.

Aegis is governed by the core operational security principle:
> **"The AI should receive only the minimum information required to perform an investigation. The LLM must never receive unrestricted database access."**

$$\text{Enterprise Data} \longrightarrow \text{Controlled Data Access} \longrightarrow \text{Data Minimization / Redaction} \longrightarrow \text{Deterministic Pseudonymization} \longrightarrow \text{Allowlisted AI Tools} \longrightarrow \text{AI Investigator} \longrightarrow \text{Structured Findings}$$

---

## 1. System Security Boundaries

```text
               ┌───────────────────────────────────────────────────┐
               │              Enterprise Data Tier                 │
               │   PostgreSQL: Orders, Customers, Tickets, Metrics │
               └─────────────────────────┬─────────────────────────┘
                                         │
                   [SERVER-SIDE CONTROLLED ACCESS LAYER]
                                         │
               ┌─────────────────────────▼─────────────────────────┐
               │           Privacy & Governance Boundary           │
               │   • DataSanitizer (Scans credentials, emails, IPs)│
               │   • Pseudonymizer (HMAC-SHA256 stable tokens)     │
               │   • Data Classification (PUBLIC/INTERNAL/CONF.)   │
               └─────────────────────────┬─────────────────────────┘
                                         │
                         [ALLOWLISTED TYPED TOOLS ONLY]
                                         │
               ┌─────────────────────────▼─────────────────────────┐
               │              AI Reasoning Boundary                │
               │   • Allowlisted tools: get_incident, get_metrics  │
               │   • Blocked: execute_sql, execute_shell, eval     │
               │   • Context bounds: Max 24h window, Max 50 records│
               │   • Prompt injection defense (Untrusted tags)     │
               │   • Zero Chain-of-Thought persistence             │
               └─────────────────────────┬─────────────────────────┘
                                         │
                        [SCHEMA-VALIDATED FINDINGS]
                                         │
               ┌─────────────────────────▼─────────────────────────┐
               │            Operator & Audit Interface             │
               │   • RBAC: VIEWER, ANALYST, OPERATOR, ADMIN        │
               │   • Anti-hallucination citation validation        │
               │   • Immutable, sanitized AuditLog ledger          │
               └───────────────────────────────────────────────────┘
```

### 1.1 Enterprise Data Boundary
Raw operational records (customer PII, payment tokens, passwords, database URLs, internal configuration) reside in persistent relational storage. Direct SQL queries and arbitrary database connections from the AI layer are strictly prohibited.

### 1.2 Privacy & Minimization Boundary
Prior to any operational data reaching an AI tool response or prompt context:
1. **Detection & Redaction**: `DataSanitizer` scans strings and structures for credentials, API keys, JWT tokens, Bearer tokens, private keys, database URLs, email addresses, phone numbers, and card numbers, replacing them with redaction tags (`[REDACTED_API_KEY]`, `[REDACTED_EMAIL]`).
2. **Deterministic Pseudonymization**: Identifiers requiring entity continuity (such as customer IDs or support tickets) are hashed using HMAC-SHA256 with a private server-side salt (`PRIVACY_SALT`). The AI sees `customer_3B9A8F1C` rather than real identities.
3. **Data Minimization**: Tools filter out extraneous fields. For example, `get_deployments` returns version and status but strips repo tokens or environment dictionaries; `get_support_tickets` returns ticket summaries but strips requester names and emails.

### 1.3 AI Tool Boundary
The AI Investigator interacts with the system exclusively through 11 allowlisted, typed application tools:
- `get_incident`, `get_timeline`, `get_anomalies`, `get_metric_window`, `compare_metrics`, `get_deployments`, `get_system_events`, `get_support_tickets`, `get_customer_complaints`, `get_impact`, `get_related_incidents`.

Forbidden tools (`execute_sql`, `execute_python`, `execute_shell`, `read_secret`, `write_database`, `network_request`) are rejected automatically with an `AI_TOOL_DENIED` audit event.

### 1.4 AI Audit & Persistence Boundary
In accordance with enterprise auditability:
- **No Hidden Chain-of-Thought**: Raw reasoning traces and hidden thinking strings are never persisted to the database.
- **Auditable Artifacts**: The system persists empirically verified `facts`, logical `inferences`, testable `hypotheses`, and `recommendations`.
- **Anti-Hallucination Evidence Validation**: Citations generated by the AI are verified against actual database records before persistence.

---

## 2. Server-Side Role-Based Access Control (RBAC)

Authorization is verified server-side on every request via `require_role(...)`:

| Role | Incident Read | Manual Ingest / Edit | Launch Investigation | Approve Recommendations | System Config & Audits |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`VIEWER`** | Read | No | No | No | No |
| **`ANALYST`** | Read | Notes & Evidence | **Yes** | No | No |
| **`OPERATOR`** | Read | Full Edit & Status | **Yes** | **Yes** | No |
| **`ADMIN`** | Read | Full Edit & Status | **Yes** | **Yes** | **Yes** |

---

## 3. Threat Model

| ID | Threat | Impact | Mitigation Strategy | Residual Risk |
| :--- | :--- | :--- | :--- | :--- |
| **T1** | **Sensitive Data Leakage to LLM** | PII or credentials exposed to third-party model providers. | `DataSanitizer` scans all tool outputs; `Pseudonymizer` replaces customer/user IDs with HMAC tokens; strict data minimization per tool. | Obfuscated or zero-day regex variations; mitigated by ongoing pattern updates and schema classification. |
| **T2** | **Arbitrary SQL Execution** | Data exfiltration, schema manipulation, or denial of service. | Direct SQL tools are forbidden; tools execute typed SQLAlchemy ORM queries with parameterized limits; arbitrary string interpolation blocked. | None in application layer; tool interface permits zero raw SQL. |
| **T3** | **Prompt Injection** | Untrusted operational text overrides system instructions to leak secrets. | Explicit boundary tags (`<UNTRUSTED_OPERATIONAL_DATA>`); system prompt mandates treating logs/tickets as untrusted data; tool execution sandboxed. | Model adherence variations; mitigated by strict tool allowlist preventing secret-reading tools. |
| **T4** | **Privilege Escalation** | Viewer executes operational changes or triggers expensive investigations. | Server-side enforcement via `require_role(...)` dependencies; role hierarchy verified on backend regardless of frontend state. | Compromise of master API key; mitigated by key rotation policies. |
| **T5** | **Secret Leakage in Logs** | Credentials or PII written to log aggregators. | Centralized `sanitize_message()` hook in `StructuredJsonFormatter` and `ConsoleFormatter` intercepts and masks sensitive data. | Exotic unformatted logging; mitigated by enforced structured logger usage. |
| **T6** | **Hallucinated Evidence** | AI invents non-existent deployments or anomaly metrics. | Server-side `_validate_evidence_citations()` compares cited IDs against retrieved database evidence; unverified citations flagged. | Low; non-matching citations are removed. |
| **T7** | **Excessive Data Retrieval** | DoS through massive time-window queries or runaway tool loops. | Configurable `MAX_QUERY_WINDOW_HOURS` (24h), `MAX_RECORDS_PER_TOOL_CALL` (50), `MAX_TOOL_CALLS_PER_INVESTIGATION` (20), and execution deadlines. | Minimal; budget tracker halts execution if thresholds exceeded. |
| **T8** | **Malicious AI-Generated Output** | AI produces malformed or dangerous JSON payloads. | Strict Pydantic schema validation (`StructuredInvestigationOutput`) enforces enums, types, and ranges before database insertion. | Low; schema validation rejects malformed responses. |
| **T9** | **Unauthorized Investigation Access** | Unauthenticated clients launch investigations or read findings. | Authentication dependency (`get_current_user`) extracts Bearer token or API key; role check required on all investigation endpoints. | Dev mode fallback when `AUTH_ENABLED=False`; strictly enforced in staging/production. |
| **T10**| **API Error Information Disclosure**| Stack traces, DB connection strings, or paths returned in HTTP 500 errors. | Global exception handler catches unhandled exceptions and returns standardized, sanitized error JSON. | None in production. |

---

## 4. Data Retention & Policy Enforcement

Retention periods are centralized in `backend/app/config.py`:
- `AUDIT_LOG_RETENTION_DAYS`: 90 days
- `INVESTIGATION_RETENTION_DAYS`: 180 days
- `OPERATIONAL_EVENT_RETENTION_DAYS`: 30 days
- `ANALYTICS_RETENTION_DAYS`: 60 days
