"""Row ↔ domain-object mapping (task T-022).

Implements docs/google-sheets-schema.md §1/§2 rules exactly: fixed header order per tab,
empty cells → null, unparseable enum/date values → invalid flagged for the reconciliation loop,
timestamp UTC ISO 8601. Duplicate task_id in column A: first occurrence wins, later ones surfaced
to the reconciliation layer.
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.models.domain import (
    ActivityEntry,
    ActivityType,
    CommandLogEntry,
    Employee,
    Priority,
    RecordSource,
    Reminder,
    ReminderStatus,
    Task,
    TaskStatus,
)
from backend.app.utils.errors import integration_error

TAB_EMPLOYEES = "Employees"
TAB_TASKS = "Tasks"
TAB_ACTIVITY = "Activity_Log"
TAB_REMINDERS = "Reminders"
TAB_COMMAND = "Command_Log"

_EMP_HEADER = ["employee_id", "name", "email", "role", "created_at"]
_TASK_HEADER = [
    "task_id", "title", "description", "assignee_id", "created_by", "status",
    "priority", "due_date", "created_at", "updated_at", "source", "external_reference",
]
_ACTIVITY_HEADER = [
    "activity_id", "employee_id", "task_id", "activity_type", "description", "timestamp", "source",
]
_REMINDER_HEADER = [
    "reminder_id", "task_id", "employee_id", "scheduled_at", "status", "created_at",
]
_COMMAND_HEADER = [
    "command_id", "timestamp", "employee_id", "conversation_id", "raw_message",
    "proposed_actions_count", "command_status", "executed_action_ids",
]
_HEADERS = {
    TAB_EMPLOYEES: _EMP_HEADER,
    TAB_TASKS: _TASK_HEADER,
    TAB_ACTIVITY: _ACTIVITY_HEADER,
    TAB_REMINDERS: _REMINDER_HEADER,
    TAB_COMMAND: _COMMAND_HEADER,
}

TASK_ID_PAT = re.compile(r"^TASK-[0-9a-f]{8}$")
EMP_ID_PAT = re.compile(r"^EMP-[0-9]{3,}$")
DATE_PAT = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def assert_header(tab: str, header: list[str]) -> None:
    expected = _HEADERS.get(tab)
    if expected is None:
        return  # unknown tab: consumers handle via their own guards
    got = [h.strip() for h in header]
    if got[: len(expected)] != expected:
        raise integration_error(
            f"Sheet tab '{tab}' header does not match the required schema (update google-sheets-schema.md).",
            {"tab": tab, "expected": expected, "found": got},
        )


def _cell(row: list[str], index: int) -> str:
    if index >= len(row):
        return ""
    value = row[index]
    return "" if value is None else str(value).strip()


def parse_task_row(row: list[str]) -> tuple[Task | None, str | None]:
    """Returns (task, invalid_reason). Corrupt enums/dates → (Their parts salvageable) reason."""
    task_id = _cell(row, 0)
    title = _cell(row, 1)
    assignee = _cell(row, 3)
    created_by = _cell(row, 4)
    status_raw = _cell(row, 5) or TaskStatus.TODO.value
    priority_raw = _cell(row, 6) or Priority.MEDIUM.value
    due_raw = _cell(row, 7)
    created_raw = _cell(row, 8)
    updated_raw = _cell(row, 9)
    source_raw = _cell(row, 10) or RecordSource.API.value
    external = _cell(row, 11) or None

    if not task_id:
        return None, "missing task_id"
    if not TASK_ID_PAT.match(task_id):
        return None, f"invalid task_id format '{task_id}'"
    if not title:
        return None, f"missing title for task {task_id}"
    if not EMP_ID_PAT.match(assignee):
        return None, f"invalid assignee_id '{assignee}' for task {task_id}"
    if not EMP_ID_PAT.match(created_by):
        return None, f"invalid created_by '{created_by}' for task {task_id}"
    if due_raw and not DATE_PAT.match(due_raw):
        return None, f"unparseable due_date '{due_raw}' for task {task_id}"
    try:
        status = TaskStatus(status_raw.upper())
        priority = Priority(priority_raw.upper())
        source = RecordSource(source_raw.upper())
    except ValueError as exc:
        return None, f"unparseable enum in task {task_id}: {exc}"
    if not created_raw:
        return None, f"missing created_at for task {task_id}"
    try:
        task = Task(
            task_id=task_id,
            title=title[:140],
            description=_cell(row, 2) or None,
            assignee_id=assignee,
            created_by=created_by,
            status=status,
            priority=priority,
            due_date=due_raw or None,
            created_at=created_raw,
            updated_at=updated_raw or created_raw,
            source=source,
            external_reference=external,
        )
    except Exception as exc:  # noqa: BLE001 — row-level validation error
        return None, f"invalid task row {task_id}: {exc}"
    return task, None


def serialize_task_row(task: Task) -> list[str]:
    return [
        task.task_id,
        task.title,
        task.description or "",
        task.assignee_id,
        task.created_by,
        task.status.value,
        task.priority.value,
        task.due_date or "",
        task.created_at,
        task.updated_at,
        task.source.value,
        task.external_reference or "",
    ]


def parse_employee_row(row: list[str]) -> Employee | None:
    emp_id, name, email, role, created = (_cell(row, i) for i in range(5))
    if not emp_id or not EMP_ID_PAT.match(emp_id):
        return None
    try:
        return Employee(
            employee_id=emp_id, name=name, email=email, role=role or "Member",
            created_at=created or "1970-01-01T00:00:00.000Z",
        )
    except Exception:  # noqa: BLE001 — row-level validation error
        return None


def parse_activity_row(row: list[str]) -> ActivityEntry | None:
    values = [_cell(row, i) for i in range(7)]
    if not values[0]:
        return None
    try:
        return ActivityEntry(
            activity_id=values[0],
            employee_id=values[1],
            task_id=values[2] or None,
            activity_type=ActivityType(values[3].upper()),
            description=values[4],
            timestamp=values[5],
            source=RecordSource(values[6].upper()) if values[6] else RecordSource.API,
        )
    except Exception:  # noqa: BLE001 — corrupt/foreign rows are tolerated (reconciliation)
        return None


def serialize_activity_row(entry: ActivityEntry) -> list[str]:
    return [
        entry.activity_id, entry.employee_id, entry.task_id or "",
        entry.activity_type.value, entry.description, entry.timestamp, entry.source.value,
    ]


def parse_reminder_row(row: list[str]) -> Reminder | None:
    values = [_cell(row, i) for i in range(6)]
    if not values[0]:
        return None
    try:
        return Reminder(
            reminder_id=values[0], task_id=values[1], employee_id=values[2],
            scheduled_at=values[3],
            status=ReminderStatus(values[4].upper()) if values[4] else ReminderStatus.SCHEDULED,
            created_at=values[5],
        )
    except Exception:  # noqa: BLE001 — corrupt/foreign rows are tolerated
        return None


def serialize_reminder_row(rem: Reminder) -> list[str]:
    return [
        rem.reminder_id, rem.task_id, rem.employee_id, rem.scheduled_at,
        rem.status.value, rem.created_at,
    ]


def serialize_command_row(cmd: CommandLogEntry) -> list[str]:
    return [
        cmd.command_id, cmd.timestamp, cmd.employee_id, cmd.conversation_id,
        cmd.raw_message.replace("\n", " ") if cmd.raw_message else "",
        str(cmd.proposed_actions_count),
        cmd.command_status,
        cmd.executed_action_ids or "",
    ]
