#!/usr/bin/env pwsh
# Development setup (Windows PowerShell) — run from the repository root.
# Assumes Python 3.11+, Node 18+, git. Fills the gaps the README skips; keeps steps idempotent.

$ErrorActionPreference = "Stop"

Write-Host "== 1/4 Python virtualenv =="
if (-not (Test-Path ".venv")) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip | Out-Null
pip install -r backend\requirements.txt
pip install -r tests\requirements.txt

Write-Host "== 2/4 Frontend dependencies =="
Push-Location frontend
if (-not (Test-Path "node_modules")) { npm install }
Pop-Location

Write-Host "== 3/4 Environment file =="
if (-not (Test-Path ".env")) { Copy-Item .env.example .env; Write-Host "Created .env — fill in values now." }

Write-Host "== 4/4 Checks =="
python scripts\validate_contracts.py
pytest -q tests --ignore=tests\integration
Write-Host "`nSetup complete. Open .env and set GOOGLE_* / OLLAMA_* values, then:"
Write-Host "  backend : .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload  (run inside backend\)"
Write-Host "  frontend: cd frontend; npm run dev"
