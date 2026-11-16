#!/usr/bin/env python
"""Development visualization tool for inspecting synthetic operational data and incident dynamics."""

import argparse
import csv
import json
from pathlib import Path
import sys

# Add backend directory to python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


def print_ascii_chart(title: str, labels: list[str], values: list[float], height: int = 10, width: int = 60) -> None:
    """Renders a simple terminal ASCII bar/sparkline chart."""
    print(f"\n--- {title} ---")
    if not values:
        print("No data available.")
        return

    min_val = min(values)
    max_val = max(values)
    val_range = max(1e-6, max_val - min_val)

    # Sample to width
    step = max(1, len(values) // width)
    sampled_vals = [values[i] for i in range(0, len(values), step)][:width]

    for h in range(height, -1, -1):
        threshold = min_val + (val_range * (h / height))
        row = ""
        for v in sampled_vals:
            row += "#" if v >= threshold else " "
        label_str = f"{threshold:8.1f} |" if h in (height, height // 2, 0) else "         |"
        print(f"{label_str} {row}")
    print(f"         +-{'-' * len(sampled_vals)}")
    print(f"           Min: {min_val:.2f} | Max: {max_val:.2f} | Samples: {len(values):,}\n")


def generate_html_dashboard(source_dir: Path, output_file: Path) -> None:
    """Builds a standalone interactive HTML/SVG visualization of the generated dataset."""
    metrics_csv = source_dir / "metrics.csv"
    scenario_json = source_dir / "incident_scenarios.json"

    if not metrics_csv.exists():
        print(f"Error: {metrics_csv} not found.")
        return

    scenario_info = {}
    if scenario_json.exists():
        with open(scenario_json, "r", encoding="utf-8") as f:
            scenarios = json.load(f)
            if scenarios:
                scenario_info = scenarios[0]

    # Read metric rows
    data_by_metric: dict[str, list[dict]] = {}
    with open(metrics_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m_name = row["metric_name"]
            if m_name not in data_by_metric:
                data_by_metric[m_name] = []
            data_by_metric[m_name].append({
                "t": row["timestamp"],
                "v": float(row["value"]),
            })

    # Prepare datasets for charting (sampled for responsive HTML payload)
    target_metrics = [
        "revenue",
        "api_error_rate",
        "api_latency",
        "checkout_failure_rate",
        "orders",
        "support_ticket_count",
    ]

    labels = []
    if "revenue" in data_by_metric:
        labels = [d["t"] for d in data_by_metric["revenue"]]

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Aegis — Synthetic Enterprise Telemetry & Incident Visualizer</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 24px;
        }}
        .header {{
            background: #1e293b;
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
            border-left: 6px solid #3b82f6;
        }}
        h1 {{ margin: 0 0 8px 0; font-size: 24px; }}
        p {{ margin: 4px 0; color: #94a3b8; font-size: 14px; }}
        .incident-badge {{
            display: inline-block;
            background: #ef4444;
            color: #fff;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 8px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 20px;
        }}
        .card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }}
        .card h2 {{
            margin-top: 0;
            font-size: 16px;
            color: #38bdf8;
        }}
        .chart-container {{
            position: relative;
            height: 260px;
        }}
        .timeline-box {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            margin-top: 24px;
            border: 1px solid #334155;
        }}
        .timeline-step {{
            padding: 8px 12px;
            border-left: 2px solid #3b82f6;
            margin-left: 8px;
            margin-bottom: 8px;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>NovaCart Operational Telemetry — 90-Day Simulation</h1>
        <p>Aegis Group 3 Synthetic Enterprise Operations Inspection</p>
        <span class="incident-badge">Injected Incident: {scenario_info.get("title", "Checkout API Degradation")}</span>
        <p style="margin-top: 10px; color: #cbd5e1;">{scenario_info.get("description", "")}</p>
    </div>

    <div class="grid">
        <div class="card">
            <h2>Hourly Revenue (USD)</h2>
            <div class="chart-container"><canvas id="chartRevenue"></canvas></div>
        </div>
        <div class="card">
            <h2>API Error Rate (%)</h2>
            <div class="chart-container"><canvas id="chartErrors"></canvas></div>
        </div>
        <div class="card">
            <h2>API Latency p95 (ms)</h2>
            <div class="chart-container"><canvas id="chartLatency"></canvas></div>
        </div>
        <div class="card">
            <h2>Checkout Failure Rate (%)</h2>
            <div class="chart-container"><canvas id="chartCheckout"></canvas></div>
        </div>
        <div class="card">
            <h2>Order Attempts vs Failed Orders</h2>
            <div class="chart-container"><canvas id="chartOrders"></canvas></div>
        </div>
        <div class="card">
            <h2>Customer Support Ticket Influx</h2>
            <div class="chart-container"><canvas id="chartSupport"></canvas></div>
        </div>
    </div>

    <div class="timeline-box">
        <h2>Causal Incident Timeline Verification</h2>
        {"".join(f'<div class="timeline-step"><strong>{item.get("time")}</strong>: {item.get("event")}</div>' for item in scenario_info.get("timeline", []))}
    </div>

    <script>
        const timestamps = {json.dumps(labels)};
        const revenue = {json.dumps([d["v"] for d in data_by_metric.get("revenue", [])])};
        const errors = {json.dumps([d["v"] * 100 for d in data_by_metric.get("api_error_rate", [])])};
        const latency = {json.dumps([d["v"] for d in data_by_metric.get("api_latency", [])])};
        const checkout = {json.dumps([d["v"] * 100 for d in data_by_metric.get("checkout_failure_rate", [])])};
        const orders = {json.dumps([d["v"] for d in data_by_metric.get("orders", [])])};
        const failedOrders = {json.dumps([d["v"] for d in data_by_metric.get("failed_orders", [])])};
        const tickets = {json.dumps([d["v"] for d in data_by_metric.get("support_ticket_count", [])])};

        function createChart(ctxId, label, data, color, yUnit = '') {{
            new Chart(document.getElementById(ctxId), {{
                type: 'line',
                data: {{
                    labels: timestamps,
                    datasets: [{{
                        label: label,
                        data: data,
                        borderColor: color,
                        backgroundColor: color + '15',
                        borderWidth: 1.5,
                        fill: true,
                        pointRadius: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        x: {{ display: false }},
                        y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }}
                    }},
                    plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }}
                }}
            }});
        }}

        createChart('chartRevenue', 'Hourly Gross Revenue ($)', revenue, '#10b981');
        createChart('chartErrors', 'API Error Rate (%)', errors, '#ef4444');
        createChart('chartLatency', 'API Latency (ms)', latency, '#f59e0b');
        createChart('chartCheckout', 'Checkout Failure Rate (%)', checkout, '#ec4899');
        createChart('chartSupport', 'Support Tickets / hr', tickets, '#8b5cf6');

        // Multi-line for orders vs failed
        new Chart(document.getElementById('chartOrders'), {{
            type: 'line',
            data: {{
                labels: timestamps,
                datasets: [
                    {{ label: 'Total Order Attempts', data: orders, borderColor: '#38bdf8', borderWidth: 1.5, pointRadius: 0 }},
                    {{ label: 'Failed Orders', data: failedOrders, borderColor: '#ef4444', borderWidth: 1.5, pointRadius: 0 }}
                ]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{ x: {{ display: false }}, y: {{ grid: {{ color: '#334155' }} }} }}
            }}
        }});
    </script>
</body>
</html>
"""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"[+] Visual dashboard written to: {output_file.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Visualize Aegis synthetic operational data.")
    parser.add_argument("--source", default="data/synthetic", help="Directory with synthetic CSV files.")
    parser.add_argument("--html-output", default="data/synthetic/visualization.html", help="HTML dashboard output file.")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.exists():
        print(f"Error: Directory {src} not found. Generate data first.")
        sys.exit(1)

    metrics_csv = src / "metrics.csv"
    if metrics_csv.exists():
        # Terminal ASCII sample
        rev_vals = []
        err_vals = []
        with open(metrics_csv, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r["metric_name"] == "revenue":
                    rev_vals.append(float(r["value"]))
                elif r["metric_name"] == "api_error_rate":
                    err_vals.append(float(r["value"]) * 100)

        print_ascii_chart("REVENUE OVER 90 DAYS (USD/hour)", [""] * len(rev_vals), rev_vals)
        print_ascii_chart("API ERROR RATE (%) - CLEAR INCIDENT SPIKE", [""] * len(err_vals), err_vals)

    generate_html_dashboard(src, Path(args.html_output))


if __name__ == "__main__":
    main()
