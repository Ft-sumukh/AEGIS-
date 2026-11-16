# Aegis Development Guide

This document covers everything required to set up, develop, test, and run Aegis locally.

---

## 1. Prerequisites

Ensure the following tools are installed on your host system:

- **Python**: 3.12+ (Python 3.12, 3.13, or 3.14)
- **Node.js**: 20.x or 22.x LTS (with npm 10+)
- **Git**: 2.40+
- **Docker & Docker Compose** (Optional for containerized run; required for full containerized stack): Docker Engine 24+ with Compose v2.

---

## 2. Quickstart (Native Local Development)

### Step 1: Clone Repository & Configure Environment
```bash
git clone https://github.com/aegis/aegis.git
cd aegis

# Copy example environment configuration
cp .env.example .env
```

### Step 2: Set Up Backend
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install backend dependencies in editable mode with dev tools
pip install -e ".[dev]"
```

### Step 3: Run Backend API
```bash
# Start backend on http://localhost:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Verify backend health in another terminal:
```bash
curl http://localhost:8000/api/v1/health
```

### Step 4: Set Up Frontend
```bash
cd ../frontend

# Install dependencies
npm install

# Start Next.js development server
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 3. Containerized Development (Docker Compose)

To start the full environment (PostgreSQL database, FastAPI backend, and Next.js frontend) with one command:

```bash
# From the repository root
docker compose up --build
```

### Docker Service Ports
- **Frontend**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000`
- **Interactive OpenAPI Docs**: `http://localhost:8000/docs`
- **PostgreSQL**: `localhost:5432`

### Stopping Containers
```bash
docker compose down
# To also delete persistent database volume:
docker compose down -v
```

---

## 4. Configuration & Environment Variables

All configuration is managed through root `.env` and loaded via Pydantic Settings in `backend/app/config.py`.

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `APP_NAME` | `Aegis` | Application name identifier |
| `APP_VERSION` | `0.1.0` | Semantic version |
| `ENVIRONMENT` | `development` | `development`, `staging`, `production`, `test` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `API_V1_PREFIX` | `/api/v1` | Root prefix for API version 1 |
| `BACKEND_PORT` | `8000` | Port for FastAPI / Uvicorn server |
| `DATABASE_URL` | `postgresql+psycopg://...` | SQLAlchemy connection string |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins for browser security |
| `AI_PROVIDER` | `mock` | Future AI provider (`mock`, `anthropic`, `openai`) |
| `AI_MODEL` | `claude-3-5-sonnet` | Model name for future agent integration |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Public API endpoint for frontend client |

---

## 5. Automated Testing

### Running Backend Tests
```bash
cd backend
# Run all tests with pytest
python -m pytest -v

# Run with test coverage report
python -m pytest --tb=short
```

---

## 6. Code Quality & Linting

### Python (Ruff)
Ruff enforces formatting, PEP 8, import sorting, and code standards:
```bash
cd backend

# Run linter
ruff check .

# Fix auto-fixable lint issues
ruff check --fix .

# Check code formatting
ruff format --check .

# Format code
ruff format .
```

### Frontend (ESLint & TypeScript)
```bash
cd frontend

# Run ESLint
npm run lint

# Check TypeScript typing
npx tsc --noEmit
```

---

## 7. Database Migrations (Alembic)

Database schema migrations are prepared using Alembic.
```bash
cd backend

# Generate a new migration revision
alembic revision --autogenerate -m "describe_migration"

# Apply pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```
