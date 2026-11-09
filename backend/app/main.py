"""Backend application entry point (scaffold — Milestone 1, task T-010).

Runs:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

Responsibilities (see backend/AGENTS.md):
- create the FastAPI app and register all routers under the /api/v1 prefix
- install the shared error-envelope exception handlers
- configure CORS from settings.CORS_ORIGINS
- wire concrete adapters into the ports defined in app.services.ports (Milestone 3)

This file is intentionally minimal right now: this repository's current milestone is the
documentation/contract foundation. Implementation proceeds task-by-task per ../tasks.md.
"""

from __future__ import annotations

API_PREFIX = "/api/v1"
__version__ = "0.1.0"
