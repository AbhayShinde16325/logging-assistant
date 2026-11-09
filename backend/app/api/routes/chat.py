"""Chat + action confirm/reject routes (tasks T-052/T-053)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.schemas.api import (
    ChatRequest,
    ChatResponse,
    ConfirmResponse,
    RejectResponse,
)
from backend.app.utils.errors import ApiError, ErrorCode

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request) -> ChatResponse:
    container = request.app.state.container
    try:
        result = container.chat_service.chat(
            payload.message,
            employee_id=payload.employee_id,
            conversation_id=payload.conversation_id,
        )
    except ApiError:
        raise
    return ChatResponse(**result)


@router.post("/actions/{action_id}/confirm", response_model=ConfirmResponse)
def confirm_action(action_id: str, request: Request) -> ConfirmResponse:
    container = request.app.state.container
    result = container.action_service.confirm(action_id)
    # contract: result wraps the created/updated resource, e.g. {"task": {...Task}}
    return ConfirmResponse(status="EXECUTED", action_id=action_id, result=result.summary)


@router.post("/actions/{action_id}/reject", response_model=RejectResponse)
def reject_action(action_id: str, request: Request) -> RejectResponse:
    container = request.app.state.container
    container.action_service.reject(action_id)
    return RejectResponse(status="REJECTED", action_id=action_id)
