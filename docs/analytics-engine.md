# Aegis Operations Intelligence & Anomaly Detection Engine

## Overview

The **Operations Intelligence Engine** (`app/analytics`) constitutes the deterministic analytical foundation of the Aegis platform. It provides high-throughput statistical baseline computation, multi-detector anomaly evaluation, severity and confidence scoring, deterministic deduplication, multi-metric correlation across an operational dependency graph, and preliminary business impact estimation.

```
                                  OPERATIONS INTELLIGENCE PIPELINE
                                  
   +-----------------------+
   |  Operational Telemetry|  (PostgreSQL / SQLite time-series)
   +-----------+-----------+
               |
               v
   +-----------------------+
   |    Baseline Engine    |  (Strictly causal: [t - W, t), no future lookahead)
   +-----------+-----------+
               |
               v
   +-----------------------+
   |   Modular Detectors   |  (Threshold, Percentage Change, Z-Score,
   |                       |   Rolling Baseline, Seasonal, Trend)
   +-----------+-----------+
               |
               v
   +-----------------------+
   |   Scorer & Fingerprint|  (Severity vs Confidence decoupled; SHA-256 deduplication)
   +-----------+-----------+
               |
               v
   +-----------------------+
   | Multi-Metric Correlator|  (Temporal clustering + Operational Dependency Graph)
   +-----------+-----------+
               |
               v
   +-----------------------+
   | Business Impact Engine|  (Financial revenue loss, blast radius estimation)
   +-----------+-----------+
               |
               v
   +-----------------------+
   |   Incident Candidate  |  (Input to Group 5 Incident Management)
   +-----------------------+
```

---

## 1. Modular Anomaly Detectors

Aegis implements six distinct detector algorithms under `app/analytics/detectors/`, each implementing the `BaseDetector` interface:

### 1.1 `ThresholdDetector`
* **Purpose**: Detects violations of configured static upper and lower warning and critical bounds.
* **Characteristics**: Produces deterministic anomalies with high base confidence (`0.95`).
* **Applicability**: Fixed SLA limits such as maximum acceptable checkout failure rates (18%), critical API error rates (8%), or minimum revenue baselines ($2000/hr).

### 1.2 `PercentageChangeDetector`
* **Purpose**: Identifies rapid rate-of-change jumps between consecutive observations ($t_{i-1}$ to $t_i$).
* **Characteristics**: Distinguishes between adverse surges (e.g. $+300\%$ jump in API latency) and adverse collapses (e.g. $-70\%$ drop in revenue).
* **Zero-Division Protection**: Uses denominator stabilization ($\max(|v_{prev}|, 10^{-5})$).

### 1.3 `ZScoreDetector`
* **Purpose**: Detects statistical outliers based on standard deviations from historical rolling means ($z = \frac{x - \mu}{\sigma}$).
* **Scoring Tiers**:
  * **Severe**: $|z| \ge 4.0\sigma$
  * **Significant**: $3.0\sigma \le |z| < 4.0\sigma$
  * **Mild**: $2.0\sigma \le |z| < 3.0\sigma$
* **Zero-Variance Guard**: Prevents division by zero when standard deviation approaches zero ($\sigma < 10^{-7} \implies \sigma = 10^{-7}$).

### 1.4 `RollingBaselineDetector`
* **Purpose**: Compares telemetry against moving historical windows without lookahead bias.
* **Strict Causality Guarantee**: Window evaluation is strictly restricted to $[t - W, t)$. Any observation where $t_p \ge t$ is strictly excluded.

### 1.5 `SeasonalDetector`
* **Purpose**: Captures cyclical time-of-day (diurnal) and day-of-week enterprise traffic dynamics.
* **Methodology**: Evaluates historical observations at the exact same hour-of-day and weekday over a 45-day lookback window, with automatic fallback to diurnal profiling if weekly samples are sparse.

### 1.6 `TrendDetector`
* **Purpose**: Discovers creeping, progressive operational degradation using ordinary least squares (OLS) linear regression.
* **Formula**:
  $$\text{slope} = \frac{\sum (x - \bar{x})(y - \bar{y})}{\sum (x - \bar{x})^2}$$
* **Normalization**: Slopes are normalized by the window mean to evaluate percentage drift per hour ($+5\%$/hr).

---

## 2. Strict Causality & Zero Lookahead Bias

A critical requirement of enterprise operations intelligence is **causal integrity**. Machine learning models and statistical baselines must never "peek into the future" when assessing the health of a system at time $t$.

In the `BaselineEngine` (`app/analytics/baseline.py`):
```python
window_start = target_timestamp - timedelta(hours=window_hours)
historical_vals = [
    p.value
    for p in series.points
    if window_start <= p.timestamp < target_timestamp  # Strictly < target_timestamp
]
```
By enforcing $p.\text{timestamp} < \text{target\_timestamp}$, post-incident degradation or recovery never contaminates the pre-incident expectation.

---

## 3. Decoupled Severity vs. Confidence & Fingerprinting

Aegis decouples an anomaly's **severity** (business/operational impact) from its **confidence** (statistical certainty):

* **Severity** (`SeverityLevel`): Determined by the metric's business importance weight and the magnitude of deviation (e.g. checkout failure rate exceeding 18% is always `CRITICAL`).
* **Confidence** ($[0.0, 1.0]$): Determined by detector algorithm certainty, baseline sample depth ($n$), and standard deviation margin.
* **Deterministic Fingerprinting**:
  To prevent duplicate anomaly records on repeat analysis runs, each anomaly generates a deterministic SHA-256 fingerprint:
  $$\text{fingerprint} = \text{SHA256}(\text{company\_id} \,\|\, \text{metric\_name} \,\|\, \text{timestamp} \,\|\, \text{detector\_type})$$
  The database ID is deterministically derived as `uuid5(company_id, fingerprint)`, ensuring completely idempotent storage.

---

## 4. Multi-Metric Correlation & Dependency Graph

An isolated metric anomaly is merely noise; a correlated cascade of anomalies across system boundaries represents an operational incident.

### Operational Dependency Graph
Aegis models the causal flow of enterprise e-commerce systems:
```
[ API Latency ] ──> [ API Errors ] ──> [ Checkout Failure Rate ] ──> [ Failed Orders ]
                                                                             │
                                                                             ├──> [ Revenue Drop ]
                                                                             └──> [ Complaints ] ──> [ Support Tickets ]
```

### Composite Correlation Scoring
When anomalies occur within a temporal clustering window (default 75 minutes), candidate pairs are evaluated across four weighted dimensions:
1. **Temporal Proximity** (35%): Closeness in time ($\Delta t \le 75$ min).
2. **Dependency Graph Connectivity** (35%): Direct edge or transitive path between metrics.
3. **Directional Alignment** (15%): Both metrics behaving adversely according to domain semantics.
4. **Severity Concordance** (15%): Concordance in severity levels.

Clusters exceeding the correlation threshold ($\ge 0.55$) are synthesized into an `IncidentCandidate`.

---

## 5. Preliminary Business Impact Estimation

For every correlated `IncidentCandidate`, the `BusinessImpactEngine` (`app/analytics/impact.py`) computes a preliminary blast radius:
* **Estimated Revenue Impact**: Cumulative financial shortfall during the anomaly window compared to the historical revenue baseline.
* **Affected Orders**: Extrapolated failed or lost orders based on order rate baselines.
* **Affected Users**: Estimated customer count encountering degraded checkouts or errors.
* **Support / Complaint Blast Radius**: Elevated complaint and support ticket influx.
* **Preliminary Flag**: All calculations are labeled `is_preliminary=True` to signal downstream consumers that root-cause verification remains pending.

---

## 6. REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/anomalies` | Paginated anomaly query with severity, status, and company filtering |
| `GET` | `/api/v1/anomalies/{id}` | Detailed inspection of a single detected anomaly |
| `GET` | `/api/v1/anomalies/summary` | Aggregated metrics (counts by severity, detector, status, and top metrics) |
| `POST` | `/api/v1/analytics/run` | Triggers detection, scoring, deduplication, correlation, and impact calculation |
| `GET` | `/api/v1/analytics/status` | Execution status and audit history of recent analytics runs |
| `GET` | `/api/v1/incident-candidates` | Lists correlated incident candidates with preliminary blast radius |

---

## 7. Benchmark Quality Evaluation

The `BenchmarkEvaluator` (`app/analytics/evaluation.py`) measures precision, recall, and $F_1$ score against synthetic ground truth incident scenarios:

$$\text{Precision} = \frac{TP}{TP + FP}, \quad \text{Recall} = \frac{TP}{TP + FN}, \quad F_1 = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

On the synthetic 65-day enterprise dataset, the engine consistently achieves:
* **Precision**: $\ge 85\%$ (resists benign promotional flash sales and batch jobs)
* **Recall**: $\ge 90\%$ (captures upstream and downstream incident symptoms)
* **$F_1$ Score**: $\ge 87\%$
