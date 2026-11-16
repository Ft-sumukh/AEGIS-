#!/usr/bin/env python3
"""Aegis Comprehensive System Evaluation & Benchmark CLI.

Runs the complete closed-loop evaluation:
  DETECT -> CORRELATE -> INVESTIGATE -> RECOMMEND -> HUMAN APPROVAL -> ACTION -> VERIFICATION -> AUDIT

Usage:
  python scripts/evaluate.py [--json] [--output report.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_dir))

from app.analytics.benchmark import AegisE2EBenchmarkRunner
from app.core.logging import setup_logging
from app.database.base import Base
from app.database.session import get_engine, get_session_factory
import app.models  # noqa: F401 Ensure models are registered on Base


def print_banner() -> None:
    print("=" * 76)
    print(" " * 18 + "AEGIS OPERATIONS INTELLIGENCE AGENT")
    print(" " * 15 + "End-to-End System Benchmark & Evaluation")
    print("=" * 76)


def format_stage(passed: bool, name: str, dur_ms: float, details: str) -> str:
    status_str = "\033[92mPASS\033[0m" if passed else "\033[91mFAIL\033[0m"
    return f"  [{status_str}] {name:<36} ({dur_ms:>7.1f} ms) - {details}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Aegis E2E System Evaluation")
    parser.add_argument("--json", action="store_true", help="Output pure JSON format")
    parser.add_argument("--output", type=str, help="Save report to specified JSON file")
    parser.add_argument("--sqlite", action="store_true", help="Force SQLite evaluation database")
    parser.add_argument("--db-url", type=str, default=None, help="Override database connection URL")
    args = parser.parse_args()

    setup_logging()

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_url = args.db_url
    if args.sqlite:
        db_url = "sqlite:///./data/benchmark.db"
    elif not db_url:
        try:
            test_engine = get_engine()
            with test_engine.connect() as conn:
                pass
            engine = test_engine
            session_factory = get_session_factory()
        except Exception:
            # Fall back to local embedded SQLite for standalone zero-dependency evaluation
            db_url = "sqlite:///./data/benchmark.db"

    if db_url and db_url.startswith("sqlite"):
        Path("./data").mkdir(exist_ok=True)
        engine = create_engine(db_url)
        session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    if not args.json:
        print_banner()
        print("\n[*] Initializing synthetic enterprise operational stream...")

    with session_factory() as session:
        runner = AegisE2EBenchmarkRunner(session)
        report = runner.run_full_benchmark()

    report_dict = report.to_dict()

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
        if not args.json:
            print(f"[+] Benchmark report saved to: {out_path.resolve()}")

    if args.json:
        print(json.dumps(report_dict, indent=2))
        return 0 if report.overall_status == "PASSED" else 1

    print("\n[*] Execution Pipeline Verification:")
    for stage in report.stages:
        print(format_stage(stage.passed, stage.stage_name, stage.duration_ms, stage.details))

    print("\n" + "-" * 76)
    print("KEY PERFORMANCE INDICATORS (CLOSED LOOP):")
    print(f"  * Detection Recall:           {report.detection_recall * 100:.1f}%")
    print(f"  * Detection Precision:        {report.detection_precision * 100:.1f}%")
    print(f"  * Detection F1 Score:         {report.detection_f1:.3f}")
    print(f"  * Mean Time to Detect (MTTD): {report.mean_time_to_detect_sec:.1f} seconds")
    print(f"  * Mean Time to Recommend:     {report.mean_time_to_recommend_sec:.1f} seconds")
    print(f"  * Human Gating Invariant:     {'STRICT ENFORCEMENT' if report.human_gating_verified else 'FAILED'}")
    print(f"  * Remediation Recovery Rate:  {report.remediation_recovery_rate * 100:.1f}%")
    print(f"  * Total Evaluation Duration:  {report.total_duration_ms:.1f} ms")
    print("-" * 76)

    if report.overall_status == "PASSED":
        print(f"\n\033[92m>>> OVERALL EVALUATION STATUS: {report.overall_status} (ALL INVARIANTS SATISFIED)\033[0m\n")
        return 0
    else:
        print(f"\n\033[91m>>> OVERALL EVALUATION STATUS: {report.overall_status}\033[0m\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
