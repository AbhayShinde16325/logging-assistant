"""Tasks routes (T-053): GET/POST/PATCH/DELETE per docs/api-contracts.md."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.models.domain import RecordSource
from backend.app.schemas.api import (
    TaskCreateIn,
    TaskListResponse,
    TaskOut,
    TaskPatchIn,
    TaskSingleResponse,
)
from backend.app.services.task_service import TaskService
from backend.app.utils.errors import validation_error

router = APIRouter(tags=["tasks"])


@router.get("/tasks", response_model=TaskListResponse)
def list_tasks(
    request: Request,
    assignee_id: str | None = None,
    status: str | None = None,
    due_before: str | None = None,
    due_after: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> TaskListResponse:
    container = request.app.state.container
    svc: TaskService = container.task_service
    tasks, total = svc.list_tasks(
        assignee_id=assignee_id,
        status=_status(status),
        due_before=due_before,
        due_after=due_after,
        limit=min(limit, 200),
        offset=max(offset, 0),
    )
    return TaskListResponse(tasks=[TaskOut.of(t) for t in tasks], total=total)


def _status(value: str | None):
    if value is None or value == "":
        return None
    from backend.app.models.domain import TaskStatus

    try:
        return TaskStatus(value.upper())
    except ValueError as exc:
        raise validation_error(f"Invalid status '{value}'.", {"status": value}) from exc


@router.get("/tasks/{task_id}", response_model=TaskSingleResponse)
def get_task(task_id: str, request: Request) -> TaskSingleResponse:
    container = request.app.state.container
    task = container.task_service.get_task(task_id)
    return TaskSingleResponse(task=TaskOut.of(task))


@router.post("/tasks", response_model=TaskSingleResponse, status_code=201)
def create_task(payload: TaskCreateIn, request: Request) -> TaskSingleResponse:
    container = request.app.state.container
    task = container.task_service.create_task(
        title=payload.title,
        assignee_id=payload.assignee_id,
        created_by=payload.assignee_id,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        source=payload.source,
        external_reference=payload.external_reference,
    )
    return TaskSingleResponse(task=TaskOut.of(task))


@router.patch("/tasks/{task_id}", response_model=TaskSingleResponse)
def patch_task(task_id: str, payload: TaskPatchIn, request: Request) -> TaskSingleResponse:
    container = request.app.state.container
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    task = container.task_service.patch_task(task_id, patch, source=RecordSource.API)
    return TaskSingleResponse(task=TaskOut.of(task))


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: str, request: Request) -> None:
    container = request.app.state.container
    container.task_service.delete_task(task_id, source=RecordSource.API)
