"""Reminders, Meetings, Voice routes (T-053, T-101, T-120)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request, UploadFile

from backend.app.models.domain import RecordSource
from backend.app.schemas.api import (
    MeetingExtractIn,
    MeetingExtractResponse,
    ReminderCreateIn,
    ReminderCreateOut,
    ReminderListResponse,
    ReminderPatchIn,
    TranscribeResponse,
)
from backend.app.utils.errors import validation_error

router = APIRouter(tags=["reminders", "meetings", "voice"])

MAX_AUDIO_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = (".webm", ".wav", ".ogg")


@router.get("/reminders", response_model=ReminderListResponse)
def list_reminders(
    request: Request,
    task_id: str | None = None,
    employee_id: str | None = None,
    status: str | None = None,
) -> ReminderListResponse:
    st = None
    if status:
        from backend.app.models.domain import ReminderStatus

        st = ReminderStatus(status.upper())
    items = request.app.state.container.reminders_service.list(
        task_id=task_id, employee_id=employee_id, status=st,
    )
    return ReminderListResponse(reminders=[ReminderCreateOut.of(r) for r in items])


@router.post("/reminders", response_model=ReminderCreateOut, status_code=201)
def create_reminder(payload: ReminderCreateIn, request: Request) -> ReminderCreateOut:
    svc = request.app.state.container.reminders_service
    rem = svc.create(
        task_id=payload.task_id, employee_id=payload.employee_id,
        scheduled_at=payload.scheduled_at, source=RecordSource.API,
    )
    return ReminderCreateOut.of(rem)


@router.patch("/reminders/{reminder_id}", response_model=ReminderCreateOut)
def patch_reminder(reminder_id: str, payload: ReminderPatchIn, request: Request) -> ReminderCreateOut:
    svc = request.app.state.container.reminders_service
    patch = payload.model_dump()
    rem = svc.patch(reminder_id, patch)
    return ReminderCreateOut.of(rem)


@router.post("/meetings/extract", response_model=MeetingExtractResponse)
def meetings_extract(payload: MeetingExtractIn, request: Request) -> MeetingExtractResponse:
    container = request.app.state.container
    result = container.meeting_service.extract(
        payload.text,
        employee_id=payload.employee_id,
        date=payload.date,
        title=payload.title,
    )
    return MeetingExtractResponse(**result)


@router.post("/voice/transcribe", response_model=TranscribeResponse)
async def voice_transcribe(audio: UploadFile, language: str = "en", request: Request = None):
    """MVP: transcription happens in the browser (Web Speech API); server-side providers were
    deliberately NOT wired (docs/api-contracts.md honesty note). Validate the upload, then return
    the contract's 501."""
    data = await audio.read()
    if not data:
        raise validation_error("Empty audio upload.", {"error": "empty_upload"})
    if len(data) > MAX_AUDIO_BYTES:
        raise validation_error("Audio must be 10MB or less.", {"error": "audio_too_large"})
    name = (audio.filename or "").lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise validation_error(
            f"Unsupported upload type {name.rsplit('.', 1)[-1]}. "
            f"Allowed: {', '.join(ALLOWED_EXTENSIONS)}.",
            {"error": "invalid_mime_type"},
        )
    from backend.app.utils.errors import ApiError, ErrorCode

    raise ApiError(
        ErrorCode.NOT_IMPLEMENTED_NOT_WIREABLE,
        "Server-side transcription is not implemented in the MVP. "
        "Use browser voice input (Web Speech API) instead — see docs/api-contracts.md.",
        {"provider": "server_side_transcription"},
        status_code=501,
    )
