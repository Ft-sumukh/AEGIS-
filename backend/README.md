# Aegis Backend

Core FastAPI service for the Aegis AI Operations Intelligence Platform.

## Requirements
- Python 3.12+
- PostgreSQL 15+

## Quickstart
```bash
# From aegis/backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```
