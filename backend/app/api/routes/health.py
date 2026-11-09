"""Health route (T-010). Per docs/api-contracts.md: component map, envelope on hard failure."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.schemas.api import HealthResponse

router = APIRouter(tags=["health"])

__version__ = "0.2.0"


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    container = request.app.state.container
    # Model failures surface through /chat per the contract note, so health never hard-fails on
    # `model_provider`; `google_sheets` "unavailable" is the documented dev/test memory mode.
    return HealthResponse(
        status="ok",
        version=__version__,
        components=container.health_components(),
    )
