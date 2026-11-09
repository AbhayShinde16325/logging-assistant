"""Employees + Activity + Dashboard routes (T-053, T-081)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.models.domain import RecordSource
from backend.app.schemas.api import (
    ActivityCreateIn,
    ActivityEntryOut,
    ActivityListResponse,
    DashboardSummary,
    EmployeeListResponse,
    EmployeeOut,
)

router = APIRouter(tags=["employees", "activity", "dashboard"])


@router.get("/employees", response_model=EmployeeListResponse)
def list_employees(request: Request) -> EmployeeListResponse:
    employees = request.app.state.container.employees.list()
    return EmployeeListResponse(employees=[EmployeeOut.of(e) for e in employees])


@router.get("/employees/{employee_id}")
def get_employee(employee_id: str, request: Request) -> dict:
    emp = request.app.state.container.employees.get(employee_id)
    if emp is None:
        from backend.app.utils.errors import not_found

        raise not_found(f"Employee '{employee_id}' not found.", {"employee_id": employee_id})
    return {"employee": EmployeeOut.of(emp).model_dump(mode="json")}


@router.get("/activity", response_model=ActivityListResponse)
def list_activity(
    request: Request,
    employee_id: str | None = None,
    task_id: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> ActivityListResponse:
    entries, total = request.app.state.container.activity.list(
        employee_id=employee_id, task_id=task_id,
        limit=min(limit, 200), offset=max(offset, 0),
    )
    return ActivityListResponse(activity=[ActivityEntryOut.of(e) for e in entries], total=total)


@router.post("/activity", response_model=ActivityEntryOut, status_code=201)
def create_activity(payload: ActivityCreateIn, request: Request) -> ActivityEntryOut:
    container = request.app.state.container
    if container.employees.get(payload.employee_id) is None:
        from backend.app.utils.errors import not_found

        raise not_found(
            f"Employee '{payload.employee_id}' not found.", {"employee_id": payload.employee_id},
        )
    if payload.task_id is not None:
        if not container.tasks.get(payload.task_id):
            from backend.app.utils.errors import not_found

            raise not_found(f"Task '{payload.task_id}' not found.", {"task_id": payload.task_id})
    entry = container.activity.append(
        employee_id=payload.employee_id,
        task_id=payload.task_id,
        activity_type=payload.activity_type,
        description=payload.description,
        source=payload.source,
    )
    return ActivityEntryOut.of(entry)


@router.get("/dashboard/summary", response_model=DashboardSummary)
def dashboard_summary(request: Request) -> DashboardSummary:
    return DashboardSummary(**request.app.state.container.dashboard_service.summary())
