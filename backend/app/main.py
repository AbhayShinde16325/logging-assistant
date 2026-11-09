"""FastAPI application factory (tasks T-010, T-080, T-101).

Run (repo root): python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
Responsibilities: routers under /api/v1, shared error envelope handlers, CORS, optional shared
bearer auth, lifespan background loops (reminders; sheets reconciliation when configured).
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from backend.app.api import dependencies as deps
from backend.app.api.routes import chat, health, misc, organize, tasks
from backend.app.core.config import get_settings
from backend.app.utils.errors import ApiError, ErrorCode

__version__ = "0.2.0"
logger = logging.getLogger("backend")


async def _run_reconciliation(reconciler, poll_seconds: int) -> None:
    while True:
        try:
            await asyncio.to_thread(reconciler.poll_once)
        except Exception:  # noqa: BLE001 — reconciliation must survive transient errors
            logger.exception("Reconciliation tick failed")
        await asyncio.sleep(poll_seconds)


def create_app(*, container=None) -> FastAPI:
    settings = get_settings()
    c = container or deps.build_container(settings)

    # -- lifespan: reminder loop + sheets reconciliation loop (defined before the app) ---
    @asynccontextmanager
    async def _lifespan(application: FastAPI):
        task_loop = asyncio.create_task(
            application.state.container.reminders_service.run_forever(poll_seconds=30.0)
        )
        poller = None
        recon = application.state.container.reconciler
        if recon is not None:
            poller = asyncio.create_task(
                _run_reconciliation(recon, application.state.container.settings.reconciliation_poll_seconds)
            )
        yield
        for t in (task_loop, poller):
            if t is not None:
                t.cancel()

    app = FastAPI(title="Personal AI Project Management Agent", version=__version__,
                  lifespan=_lifespan)
    app.state.container = c

    # -- middleware --------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class SharedTokenAuth(BaseHTTPMiddleware):
        """Optional shared bearer token (API_BEARER_TOKEN); off when unset (MVP local tool)."""

        async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
            expected = settings.api_bearer_token
            if expected:
                provided = request.headers.get("authorization", "")
                if provided != f"Bearer {expected}":
                    err = ApiError(ErrorCode.UNAUTHORIZED, "Missing or invalid bearer token.", {}, 401)
                    return JSONResponse(err.envelope(), status_code=401)
            return await call_next(request)

    app.add_middleware(SharedTokenAuth)

    # -- error envelope handlers (root AGENTS.md §3) ------------------------------
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(exc.envelope(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        err = ApiError(
            ErrorCode.VALIDATION_ERROR,
            "The request payload failed validation.",
            {"issues": exc.errors()},
            422,
        )
        return JSONResponse(err.envelope(), status_code=422)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server error")
        err = ApiError(ErrorCode.INTERNAL_ERROR, "An unexpected server error occurred.", {}, 500)
        return JSONResponse(err.envelope(), status_code=500)

    # -- routes --------------------------------------------------------------------
    for router in (
        health.router, chat.router, tasks.router, organize.router, misc.router,
    ):
        app.include_router(router, prefix="/api/v1")

    return app


def _default_app() -> FastAPI:
    """Built lazily so importing this module (tests) never constructs the default container."""
    return create_app()


def __getattr__(name: str):  # module-level PEP 562 hook (uvicorn resolves `main:app` lazily)
    if name == "app":
        return _default_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
