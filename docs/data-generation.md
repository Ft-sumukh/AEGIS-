# Aegis Synthetic Enterprise Data Generation & Ingestion Subsystem

This document outlines the architecture, mathematical formulations, causal modeling, incident injection mechanics, ingestion pipeline, idempotency protocols, and privacy safeguards for **Aegis Group 3: Synthetic Enterprise Data Generation & Data Ingestion**.

---

## 1. Executive Summary & Enterprise Context

Aegis is an enterprise-grade AI Operations Intelligence Agent designed to ingest telemetry, monitor operational metrics, detect anomalies, correlate multi-source signals, investigate root causes, and execute verified remediation.

To develop, validate, and benchmark Aegis without exposing proprietary enterprise data, Group 3 establishes a **simulated living enterprise environment** for **NovaCart Inc.**, a high-volume omnichannel e-commerce platform.

### Key Capabilities

* **High-Fidelity 90-Day Simulation**: 2,160 continuous hourly observations across 12 core operational metrics (>25,000 telemetry points), 25,000+ orders, 1,500 synthetic customers, 10 deployments, 140 system events, and thousands of customer support signals.
* **Strict Causal Coupling**: Metrics are computed via explicit dependency trees rather than independent random numbers.
* **Deterministic Reproducibility**: Seeding (`--seed 42`) yields bit-for-bit identical datasets across generation runs.
* **Injected Operational Incidents**: Features a multi-hour catastrophic degradation cascade triggered by an erroneous deployment (`checkout-service` `v4.8.2`), exhibiting measurable statistical deviation followed by an emergency rollback (`v4.8.1`) and recovery.
* **Benign Secondary Anomalies**: Distinguishes true incidents from non-incident fluctuations (e.g. marketing campaigns, transient cloud ISP blips).
* **Idempotent Ingestion Pipeline**: Parses CSV/JSON, validates types/ranges/enums, enforces foreign-key referential integrity, detects duplicates, executes chunked batch database insertion, and produces structured audit reports.
* **Zero-Leakage Privacy Safeguards**: 100% synthetic identities restricted to `@example.com` domains and `+1-555-*` telephone masks, classified as `PUBLIC_DEMO`.

---

## 2. Mathematical Modeling & Causal Dynamics

Aegis does not generate operational metrics independently. Independent metrics destroy cross-metric correlations, making root-cause analysis impossible for downstream AI investigation agents. Group 3 implements explicit mathematical causal flows.

```
Traffic (Requests/hr)
       │
       ▼
Active Users (Browsing Sessions)
       │
       ▼
Buyer Attempt Rate ───► Checkout Attempts
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
       Failed Checkouts               Completed Orders
                │                             │
    ┌───────────┴───────────┐                 ▼
    ▼                       ▼          Gross Revenue ($)
Support Tickets     Complaints
```

### 2.1 Diurnal & Weekly Seasonality Profiles

Traffic volume $T(t)$ at timestamp $t$ is defined as:

$$T(t) = T_{\text{base}} \times D(h(t)) \times W(d(t)) \times M(t) \times \epsilon_{\text{traffic}}$$

Where:
* $T_{\text{base}} = 12,000 \text{ requests/hour}$ baseline traffic.
* $D(h)$: Diurnal hourly factor ($h \in [0, 23]$):
  * **00:00–05:00**: Nighttime trough ($0.16–0.28\times$).
  * **06:00–11:00**: Morning ramp-up ($0.45–1.25\times$).
  * **12:00–17:00**: Sustained afternoon activity ($1.12–1.24\times$).
  * **18:00–21:00**: Prime evening shopping peak ($1.28–1.35\times$).
  * **22:00–23:00**: Late-evening taper ($0.45–0.75\times$).
* $W(d)$: Weekly factor ($d \in [0, 6]$, Monday=0, Sunday=6):
  * Weekday baseline ($0.98–1.04\times$).
  * Friday payday surge ($1.15\times$).
  * Sunday evening checkout peak ($1.18\times$).
* $M(t)$: Macro annual sinusoidal drift: $1.0 + 0.05 \sin\left(\frac{2\pi \cdot \text{day}}{365.25}\right)$.
* $\epsilon_{\text{traffic}} \sim \mathcal{N}(1.0, 0.035)$: Bounded Gaussian noise.

### 2.2 Conversion, Order Volumes & Revenue

1. **Active Users**: $U(t) = \text{round}(T(t) \times \mathcal{N}(0.35, 0.02))$.
2. **Checkout Attempts**: $O_{\text{attempt}}(t) = \text{round}(U(t) \times C_{\text{attempt}}(t))$.
   * Under normal conditions: $C_{\text{attempt}} \approx 3.2\%$.
   * Under API degradation with user cart abandonment: $C_{\text{attempt}}(t) = C_{\text{base}} \times (1.0 - 0.45 \cdot \delta(t))$.
3. **Failed Orders**: $O_{\text{fail}}(t) = \text{round}(O_{\text{attempt}}(t) \times R_{\text{fail}}(t))$.
4. **Completed Orders**: $O_{\text{success}}(t) = \max(0, O_{\text{attempt}}(t) - O_{\text{fail}}(t))$.
5. **Realized Conversion Rate**: $\text{CR}(t) = \frac{O_{\text{success}}(t)}{U(t)}$.
6. **Order Value Distribution**: Derived using a Log-Normal distribution $\text{Lognormal}(\mu, \sigma)$ with mean $\mu_{\text{target}} = \$85.50$ and $\sigma = 0.55$:
   $$\text{AOV} \sim \text{Lognormal}(\ln(85.5) - 0.55^2 / 2, 0.55)$$
   Produces realistic order amounts: high frequency of $\$35–\$90$ baskets, fewer $\$120–\$250$ purchases, and rare $\$400–\$750$ large orders.
7. **Gross Revenue**: $\text{Rev}(t) = O_{\text{success}}(t) \times \text{AOV}(t)$.

### 2.3 Support Feedback & Ingress Degradation

* **API Latency**: Baseline $\sim 120\text{ms} \pm 8\text{ms}$. Surges up to $920\text{ms}$ during connection starvation.
* **API Error Rate**: Baseline $\sim 0.2\% \pm 0.05\%$. Surges up to $16.5\%$ during connection starvation.
* **Support Tickets**: Arrival modeled as a Poisson process:
  $$\lambda_{\text{ticket}}(t) = \max(0.5, O_{\text{attempt}}(t) \times 0.015) + (0.35 \times O_{\text{fail}}(t))$$
* **Customer Complaints**:
  $$\lambda_{\text{complaint}}(t) = \max(0.2, O_{\text{attempt}}(t) \times 0.005) + (0.22 \times O_{\text{fail}}(t))$$

---

## 3. Incident Simulation Framework

### 3.1 Primary Incident: Checkout API Database Pool Exhaustion

The primary operational incident (`INC-20260731-001`) simulates a real-world infrastructure failure: a misconfigured HikariCP database connection pool introduced in production deployment `v4.8.2` of `checkout-service`.

```
09:14 UTC  Deployment checkout-service v4.8.2 released to production
    │
09:19 UTC  HikariCP active connections reach 5/5 ceiling
    │
09:20 UTC  p95 API latency begins rapid escalation (120ms -> 340ms)
    │
09:23 UTC  HikariPool-1 throws SQLTransientConnectionException (30s timeout)
    │
09:25 UTC  API Gateway logs surge in HTTP 504 Gateway Timeouts (Error rate -> 8.5%)
    │
09:30 UTC  Checkout failure rate escalates past 25%
    │
09:40 UTC  Order processing thread exhaustion; failed orders surge
    │
09:48 UTC  PagerDuty High Severity Alert triggers: Checkout API Error Rate > 10%
    │
09:50 UTC  Customer complaints surge regarding failed payment card transactions
    │
10:00 UTC  Customer support queue inundated with critical checkout failure tickets
    │
10:15 UTC  Gross hourly order revenue plunges by >70% compared to diurnal baseline
    │
13:58 UTC  SRE On-Call initiates emergency rollback deployment v4.8.1
    │
14:00 UTC  Deployment v4.8.1 live in production; max_connections restored to 50
    │
14:30 UTC  Error rates decline below 2%; checkout failures subside
    │
18:00 UTC  Full operational recovery; support backlogs cleared; alerts resolved
```

### 3.2 Statistical Verification

Automated tests in `backend/tests/test_incident_simulation.py` statistically verify this causal cascade:

| Metric | Pre-Incident Baseline (Day 59, 10–13h) | Incident Peak (Day 60, 10–13h) | Shift Factor | Recovery Target (Day 60, 19–22h) |
| :--- | :--- | :--- | :--- | :--- |
| **API Error Rate** | $0.20\%$ | $14.2\%$ | **$>70\times$ increase** | $< 1.0\%$ |
| **API Latency (p95)** | $119.8\text{ ms}$ | $835.4\text{ ms}$ | **$>6.9\times$ increase** | $< 180.0\text{ ms}$ |
| **Checkout Failure Rate** | $1.22\%$ | $43.8\%$ | **$>35\times$ surge** | $< 2.5\%$ |
| **Hourly Revenue** | $\$14,392.93$ | $\$3,481.12$ | **$>75\%$ drop** | Normal diurnal baseline |
| **Hourly Support Tickets** | $\sim 3\text{ tickets/hr}$ | $\sim 38\text{ tickets/hr}$ | **$>12\times$ surge** | $\sim 2\text{ tickets/hr}$ |

### 3.3 Benign Secondary Anomalies

To ensure that downstream anomaly detection models do not flag every fluctuation as an emergency incident, the dataset includes:

1. **Day 22 Marketing Campaign**: Traffic increases by $+55\%$ and orders increase proportionally, but error rate remains healthy ($<0.5\%$).
2. **Day 45 Transient Network Blip**: Cloud gateway latency briefly jumps to $285\text{ms}$ for a single hour, with zero dropped orders and zero checkout failures.
3. **Day 75 Weekend Flash Sale**: Elevated conversion rate ($+22\%$) and healthy revenue surge.

---

## 4. Ingestion Pipeline Architecture

The ingestion pipeline is completely decoupled from the data generator. The generator outputs raw tabular CSV and JSON files; the ingestion engine parses, validates, normalizes, deduplicates, and batch-loads records into PostgreSQL.

```
RAW DATA FILES (CSV / JSON)
            │
            ▼
     DatasetParser
  (Streaming row reader)
            │
            ▼
      DataValidator
  (Schema, Types, Bounds, Enums, FKs)
            │
            ▼
     BatchDataLoader
  (1,000-row chunks, Idempotency Deduplication)
            │
            ▼
     IngestionReport
  (Audit trail of received, inserted, rejected, duplicates)
```

### 4.1 Validation Layers

1. **Mandatory Field & Type Checking**: Enforces presence of primary identifiers, external references, and valid UUID formats.
2. **Timestamp Parsing**: Conforms ISO 8601 strings into UTC-aware datetime objects (`UTCDateTime`).
3. **Range & Sanity Verification**: Validates non-negative order amounts, positive order item quantities, and rate metrics bounded in $[0.0, 1.0]$.
4. **Enum Conformance**: Maps raw string values to strictly typed Python/SQLAlchemy enums (`OrderStatus`, `DeploymentStatus`, `SeverityLevel`, `TicketPriority`, `TicketStatus`).
5. **Referential Integrity**: Verifies in-memory that every order references an ingested customer and every order item references an ingested order.

### 4.2 Idempotency & Batch Performance

* **Idempotency Strategy**:
  * **Customers & Orders**: Deduplicated against existing `(company_id, external_reference)`.
  * **Telemetry Metrics, Events, Deployments, Tickets, Complaints**: Deduplicated against deterministic primary keys (`UUIDv5` namespace hashes).
  * **Rerun Guarantee**: Rerunning the ingestion pipeline against an existing database inserts $0$ new rows and classifies $100\%$ of repeated records as duplicate skips without failing or raising primary key collisions.
* **Batch Insertion**: Inserts entities in chunked transactions (default: 1,000 rows per transaction) to optimize PostgreSQL connection overhead and avoid memory bloat.

---

## 5. CLI Reference Guide

The unified CLI tool is located at `scripts/manage_data.py` (and `backend/app/cli.py`).

### 5.1 Generate Dataset

```powershell
python scripts/manage_data.py generate-data --days 90 --seed 42 --customers 1500 --output-dir data/synthetic
```

**Options**:
* `--days <int>`: Simulation duration in days (default: `90`).
* `--seed <int>`: Deterministic random seed (default: `42`).
* `--customers <int>`: Size of synthetic customer population (default: `1500`).
* `--output-dir <path>`: Output directory for CSV and JSON files (default: `data/synthetic`).
* `--company <str>`: Enterprise company name (default: `NovaCart`).

### 5.2 Validate Dataset

```powershell
python scripts/manage_data.py validate-data --source data/synthetic --format csv
```

**Options**:
* `--source <path>`: Directory containing dataset files (default: `data/synthetic`).
* `--format [csv|json]`: File format to validate (default: `csv`).

### 5.3 Visualize Dataset

```powershell
python scripts/visualize_data.py --source data/synthetic
```

Generates:
* **Terminal ASCII Charts**: Immediate visual preview of revenue trends and the API error rate incident spike.
* **Interactive HTML Dashboard**: Written to `data/synthetic/visualization.html`, viewable in any browser.

### 5.4 Ingest Dataset

```powershell
python scripts/manage_data.py ingest-data --source data/synthetic --format csv --batch-size 1000
```

**Options**:
* `--source <path>`: Directory containing dataset files (default: `data/synthetic`).
* `--format [csv|json]`: File format to ingest (default: `csv`).
* `--batch-size <int>`: Chunk size for transactional database insertion (default: `1000`).
* `--db-url <url>`: Optional custom database connection string (e.g. SQLite test file or PostgreSQL).

### 5.5 Reset Demo Data

```powershell
python scripts/manage_data.py reset-demo-data --company-slug novacart --source data/synthetic --format csv
```

Purges the existing demo company and all cascading child records, then performs a fresh ingestion run.

---

## 6. API Endpoints

Aegis provides aggregate inspection endpoints at `/api/v1/data`:

| Method | Endpoint | Description | Response Model |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/data/sources` | Lists registered telemetry sources and supported formats | Source metadata JSON |
| `GET` | `/api/v1/data/summary` | Aggregate operational row counts and time horizons across all tables | Entity counts & timestamp boundaries |
| `GET` | `/api/v1/data/quality` | Data validation health, hygiene posture, and privacy certification | Quality & privacy compliance report |

> [!NOTE]
> In accordance with privacy minimization, individual customer records and PII are never exposed through public query endpoints.

---

## 7. Privacy & Data Governance

Even within synthetic generation environments, Aegis enforces enterprise-grade privacy controls:

1. **Synthetic Isolation**: All generated customer email addresses belong exclusively to `@example.com` (RFC 2606 reserved domain).
2. **Pseudonymous Identifiers**: Telemetry references customer accounts using opaque external identifiers (`CUST-000001` through `CUST-001500`).
3. **No Real PII**: No real names, payment account numbers (PAN), credit card details, or sensitive credentials are ever generated or ingested.
4. **Data Classification**: All synthetic enterprise artifacts are formally classified as `PUBLIC_DEMO`.
