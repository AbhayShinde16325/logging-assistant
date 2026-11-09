"""Ports (task T-012) — the interfaces A defines and Bimplements against.

docs/architecture.md §3: the backend depends on these protocols ONLY — concrete Google/Ollama
adapters are injected in app/api/dependencies.py. B implements them in
integrations/google_sheets/repository.py; in-memory implementations for tests/dev-MVP live in
app/services/memory.py (documented as dev/test fallback).

All mutation methods log to the Activity_Log themselves (T-060) so every state change is tracked
regardless of the storage backend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from backend.app.models.domain import (
    ActivityEntry,
    ActivityType,
    Employee,
    Priority,
    RecordSource,
    Reminder,
    ReminderStatus,
    Task,
    TaskStatus,
)


class ClockPort(Protocol):
    def utcnow(self) -> datetime: ...


class EmployeeRepository(Protocol):
    def list(self) -> list[Employee]: ...
    def get(self, employee_id: str) -> Employee | None: ...


class TaskRepository(Protocol):
    def create(
        self,
        *,
        title: str,
        assignee_id: str,
        created_by: str,
        description: str | None = None,
        status: TaskStatus = TaskStatus.TODO,
        priority: Priority = Priority.MEDIUM,
        due_date: str | None = None,
        source: RecordSource = RecordSource.API,
        external_reference: str | None = None,
    ) -> Task: ...

    def get(self, task_id: str) -> Task | None: ...

    def list_tasks(
        self,
        *,
        assignee_id: str | None = None,
        status: TaskStatus | None = None,
        title_contains: str | None = None,
        due_before: str | None = None,
        due_after: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[Task], int]: ...

    def find_open_duplicate(self, assignee_id: str, title: str) -> Task | None: ...

    def update(self, task_id: str, patch: dict[str, Any], *, source: RecordSource) -> Task | None: ...

    def delete(self, task_id: str, *, source: RecordSource) -> bool: ...


class ActivityLogRepository(Protocol):
    def append(
        self,
        *,
        employee_id: str,
        task_id: str | None,
        activity_type: ActivityType,
        description: str,
        source: RecordSource,
        timestamp: datetime | None = None,
    ) -> ActivityEntry: ...

    def list(
        self,
        *,
        employee_id: str | None = None,
        task_id: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> tuple[list[ActivityEntry], int]: ...


class ReminderRepository(Protocol):
    def create(
        self, *, task_id: str, employee_id: str, scheduled_at: str,
        source: RecordSource = RecordSource.API,
    ) -> Reminder: ...

    def get(self, reminder_id: str) -> Reminder | None: ...

    def list(
        self,
        *,
        task_id: str | None = None,
        employee_id: str | None = None,
        status: ReminderStatus | None = None,
    ) -> list[Reminder]: ...

    def update_status(self, reminder_id: str, status: ReminderStatus) -> Reminder | None: ...


class CommandLogRepository(Protocol):
    """Command_Log (docs/data-model.md) — written by chat/confirm/reject flows."""

    def append(
        self, *, employee_id: str, conversation_id: str, raw_message: str,
        proposed_actions_count: int, command_status: str, timestamps: datetime | None = None,
    ) -> str: ...

    def update_status(self, command_id: str, command_status: str, executed_action_ids: str) -> None: ...


class ServiceDefaults:
    """Shared validation constants for duplicates/schema level rules (docs/data-model.md)."""

    OPEN_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
