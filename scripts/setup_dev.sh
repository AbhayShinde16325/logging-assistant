#!/usr/bin/env bash
# Development setup (macOS/Linux) — run from the repository root. Idempotent.
set -euo pipefail

echo "== 1/4 Python virtualenv =="
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip >/dev/null
pip install -r backend/requirements.txt
pip install -r tests/requirements.txt

echo "== 2/4 Frontend dependencies =="
( cd frontend && [ -d node_modules ] || npm install )

echo "== 3/4 Environment file =="
[ -f .env ] || { cp .env.example .env; echo "Created .env — fill in values now."; }

echo "== 4/4 Checks =="
python scripts/validate_contracts.py
pytest -q tests --ignore=tests/integration

echo
echo "Setup complete. Open .env and set GOOGLE_* / OLLAMA_* values, then:"
echo "  backend : source .venv/bin/activate && cd backend && uvicorn app.main:app --reload"
echo "  frontend: cd frontend && npm run dev"
