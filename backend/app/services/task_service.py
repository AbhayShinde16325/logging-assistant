"""Task service — business rules over the ports (task T-051 validation layering).

Entity-level rules live here (duplicate detection, FK validation); schema-level validation is
Pydantic at the route; context-level re-validation happens in action_service at confirm time.
"""

from __future__ import annotations

from typing import Any

from backend.app.models.domain import (
    Employee,
    Priority,
    RecordSource,
    Task,
    TaskStatus,
)
from backend.app.services.memory import MemoryEmployeeRepository, MemoryTaskRepository
from backend.app.services.ports import EmployeeRepository, TaskRepository
from backend.app.utils.errors import conflict, not_found, validation_error


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository | MemoryTaskRepository,
        employees: EmployeeRepository | MemoryEmployeeRepository,
    ) -> None:
        self.tasks = tasks
        self.employees = employees

    # -- helpers ----------------------------------------------------------------
    def _require_employee(self, employee_id: str, label: str) -> Employee:
        emp = self.employees.get(employee_id)
        if emp is None:
            raise not_found(f"Unknown {label} '{employee_id}' (employees live in the sheet).",
                            {"employee_id": employee_id})
        return emp

    def create_task(
        self, *, title: str, assignee_id: str, created_by: str,
        description: str | None = None, status: TaskStatus = TaskStatus.TODO,
        priority: Priority = Priority.MEDIUM, due_date: str | None = None,
        source: RecordSource = RecordSource.API, external_reference: str | None = None,
    ) -> Task:
        self._require_employee(assignee_id, "assignee")
        self._require_employee(created_by, "creator")
        dup = self.tasks.find_open_duplicate(assignee_id, title)
        if dup is not None:
            raise conflict(
                f"An open task with the same title already exists for this assignee: "
                f"'{dup.title}' ({dup.task_id}). Use PATCH /tasks/{dup.task_id} instead.",
                {"existing_task_id": dup.task_id},
            )
        return self.tasks.create(
            title=title,
            assignee_id=assignee_id,
            created_by=created_by,
            description=description,
            status=status,
            priority=priority,
            due_date=due_date,
            source=source,
            external_reference=external_reference,
        )

    def get_task(self, task_id: str) -> Task:
        task = self.tasks.get(task_id)
        if task is None:
            raise not_found(f"Task '{task_id}' not found.", {"task_id": task_id})
        return task

    def list_tasks(self, **filters: Any) -> tuple[list[Task], int]:
        return self.tasks.list_tasks(**filters)

    def patch_task(
        self, task_id: str, patch: dict[str, Any], *, source: RecordSource,
    ) -> Task:
        task = self.tasks.get(task_id)
        if task is None:
            raise not_found(f"Task '{task_id}' not found.", {"task_id": task_id})
        if patch.get("assignee_id"):
            self._require_employee(patch["assignee_id"], "assignee")
        # normalize/coerce raw values (agent payloads contain strings) via the contract schema
        normalized_in: dict[str, Any] = {}
        for key, value in patch.items():
            if key in ("status", "priority") and isinstance(value, str):
                value = value.upper()
            normalized_in[key] = value
        from backend.app.schemas.api import TaskPatchIn

        normalized = TaskPatchIn.model_validate(normalized_in)
        patch = normalized.model_dump(exclude_none=True)
        if not patch:
            raise validation_error("PATCH requires at least one field.")
        updated = self.tasks.update(task_id, patch, source=source)
        if updated is None:
            raise not_found(f"Task '{task_id}' not found.", {"task_id": task_id})
        return updated

    def delete_task(self, task_id: str, *, source: RecordSource) -> None:
        ok = self.tasks.delete(task_id, source=source)
        if not ok:
            raise not_found(f"Task '{task_id}' not found.", {"task_id": task_id})

    def validate_employees_exist(self, *ids: str) -> None:
        for e in ids:
            self._require_employee(e, "employee")


def find_open_duplicate(tasks: TaskRepository, assignee_id: str, title: str) -> Task | None:
    return tasks.find_open_duplicate(assignee_id, title)
