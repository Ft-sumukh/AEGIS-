#!/usr/bin/env python
"""Aegis CLI wrapper script for data generation, validation, and ingestion."""

import sys
from pathlib import Path

# Add backend directory to python path
backend_path = Path(__file__).resolve().parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.cli import cli

if __name__ == "__main__":
    cli()
