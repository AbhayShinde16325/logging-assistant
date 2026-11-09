"""Google Sheets repositories implementing the ports defined by A (task T-023).

Rules (integrations/AGENTS.md + docs/google-sheets-schema.md):
- Rows located by exact ID match in column A — row numbers are NEVER identity.
- Every mutation appends an Activity_Log row (T-060); callers can't forget.
- Failures surface typed integration errors (routes map them to the 502 envelope).
Fake-client test mode (tests/unit/FakeGoogleSheetsClient) drives this code against an in-memory
sheet — no credentials needed for unit tests (mapping: docs/testing-strategy.md).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend.app.core.config import Settings
from backend.app.models.domain import (
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
from backend.app.services.ports import ServiceDefaults
from backend.app.utils.errors import integration_error, not_found
from backend.app.utils.ids import DEFAULT_CLOCK, Clock, new_id, to_iso

from . import mapper
from .client import GoogleSheetsApiClient
from .memory_client import MemorySheetsClient

logger = logging.getLogger("integrations.google_sheets")


class SheetsActivityLogRepository:
    """Append-only Activity_Log (T-060) — shared access point for every mutation."""

    def __init__(self, client: Any, clock: Clock = DEFAULT_CLOCK) -> None:
        self.client = client
        self.clock = clock

    def append(
        self, *, employee_id: str, task_id: str | None, activity_type: ActivityType,
        description: str, source: RecordSource, timestamp: datetime | None = None,
    ):
        from backend.app.models.domain import ActivityEntry

        ts = to_iso(timestamp or self.clock.utcnow())
        row = [
            new_id("LOG"), employee_id, task_id or "", activity_type.value,
            description[:500], ts, source.value,
        ]
        self.client.append_row(mapper.TAB_ACTIVITY, row, header=mapper._ACTIVITY_HEADER)
        return ActivityEntry(
            activity_id=row[0], employee_id=employee_id, task_id=task_id,
            activity_type=activity_type, description=description[:500],
            timestamp=ts, source=source,
        )

    def list(
        self, *, employee_id: str | None = None, task_id: str | None = None,
        limit: int = 200, offset: int = 0,
    ):
        from backend.app.models.domain import ActivityEntry

        rows = self.client.get_rows(mapper.TAB_ACTIVITY)
        entries = [mapper.parse_activity_row(r) for r in rows]
        entries = [e for e in entries if e is not None]
        if employee_id:
            entries = [e for e in entries if e.employee_id == employee_id]
        if task_id:
            entries = [e for e in entries if e.task_id == task_id]
        entries.sort(key=lambda e: (e.timestamp, e.activity_id))
        total = len(entries)
        return entries[offset:offset + limit], total


class SheetsEmployeeRepository:
    """Employees are manually maintained in the sheet (ADR-002); read-only here — and never
    exposed to writes from the agent."""

    def __init__(self, client: Any) -> None:
        self.client = client
        self._cache: dict[str, Employee] | None = None  # short snapshot (name resolution)

    def _load(self) -> dict[str, Employee]:
        if self._cache is None:
            rows = self.client.get_rows(mapper.TAB_EMPLOYEES)
            self._cache = {}
            for row in rows:
                emp = mapper.parse_employee_row(row)
                if emp is not None:
                    self._cache.setdefault(emp.employee_id, emp)
        return dict(self._cache)

    def invalidate(self) -> None:
        self._cache = None

    def list(self) -> list[Employee]:
        self.invalidate()
        employees = list(self._load().values())
        employees.sort(key=lambda e: e.employee_id)
        return employees

    def get(self, employee_id: str) -> Employee | None:
        return self._load().get(employee_id)


class SheetsTaskRepository:
    def __init__(
        self, client: Any, employees: SheetsEmployeeRepository,
        activity: SheetsActivityLogRepository, clock: Clock = DEFAULT_CLOCK,
    ) -> None:
        self.client = client
        self.employees = employees
        self.activity = activity
        self.clock = clock

    # -- low-level row handling -------------------------------------------------
    def _load_all(self) -> tuple[list[Task], dict[str, int], list[str]]:
        rows = self.client.get_rows(mapper.TAB_TASKS)
        tasks: list[Task] = []
        row_numbers: dict[str, int] = {}
        invalid: list[str] = []
        for idx, row in enumerate(rows, start=2):  # header is row 1
            task, reason = mapper.parse_task_row(row)
            if task is None:
                if reason and not any(c.strip() for c in row):
                    continue  # blank row — tolerated
                invalid.append(reason or f"unreadable row {idx}")
                continue
            if task.task_id in row_numbers:
                invalid.append(
                    f"duplicate task_id {task.task_id} (row {idx} shadowed by earlier row)"
                )
                continue
            row_numbers[task.task_id] = idx
            tasks.append(task)
        return tasks, row_numbers, invalid

    # -- port: create ------------------------------------------------------------
    def create(
        self, *, title: str, assignee_id: str, created_by: str,
        description: str | None = None, status: TaskStatus = TaskStatus.TODO,
        priority: Priority = Priority.MEDIUM, due_date: str | None = None,
        source: RecordSource = RecordSource.API, external_reference: str | None = None,
    ) -> Task:
        now = to_iso(self.clock.utcnow())
        task = Task(
            task_id=new_id("TASK"),
            title=title.strip()[:140],
            description=description or None,
            assignee_id=assignee_id,
            created_by=created_by,
            status=status,
            priority=priority,
            due_date=due_date,
            created_at=now,
            updated_at=now,  # app-write marker used by reconciliation's self-write guard
            source=source,
            external_reference=external_reference,
        )
        self.client.append_row(mapper.TAB_TASKS, mapper.serialize_task_row(task),
                               header=mapper._TASK_HEADER)
        self.activity.append(
            employee_id=created_by, task_id=task.task_id,
            activity_type=ActivityType.TASK_CREATED,
            description=f"Created task '{task.title}' (assignee {assignee_id}).",
            source=source,
        )
        return task

    # -- port: read ---------------------------------------------------------------
    def get(self, task_id: str) -> Task | None:
        tasks, _, _ = self._load_all()
        for t in tasks:
            if t.task_id == task_id:
                return t
        return None

    def get_or_404(self, task_id: str) -> Task:
        task = self.get(task_id)
        if task is None:
            raise not_found(
                f"Task '{task_id}' not found (it may have been removed from the sheet "
                "or the ID is wrong).",
                {"task_id": task_id},
            )
        return task

    def list_tasks(
        self, *, assignee_id: str | None = None, status: TaskStatus | None = None,
        title_contains: str | None = None, due_before: str | None = None,
        due_after: str | None = None, limit: int = 200, offset: int = 0,
    ) -> tuple[list[Task], int]:
        tasks, _, invalid = self._load_all()
        if invalid:
            logger.warning("Skipped unreadable Tasks rows: %s", "; ".join(invalid))
        needle = (title_contains or "").lower().strip() or None
        items: list[Task] = []
        for t in tasks:
            if assignee_id and t.assignee_id != assignee_id:
                continue
            if status and t.status != status:
                continue
            if needle and needle not in t.title.lower():
                continue
            if due_before and not (t.due_date and t.due_date <= due_before):
                continue
            if due_after and not (t.due_date and t.due_date >= due_after):
                continue
            items.append(t)
        items.sort(key=lambda t: (t.due_date or "9999-12-31", t.created_at))
        total = len(items)
        return items[offset:offset + limit], total

    def find_open_duplicate(self, assignee_id: str, title: str) -> Task | None:
        needle = " ".join(title.lower().split())
        tasks, _, _ = self._load_all()
        for t in tasks:
            if (
                t.assignee_id == assignee_id
                and t.status in ServiceDefaults.OPEN_STATUSES
                and " ".join(t.title.lower().split()) == needle
            ):
                return t
        return None

    # -- port: update -----------------------------------------------------------
    def update(
        self, task_id: str, patch: dict[str, Any], *, source: RecordSource,
    ) -> Task | None:
        tasks, row_numbers, _ = self._load_all()
        current = next((t for t in tasks if t.task_id == task_id), None)
        if current is None:
            return None
        row_number = row_numbers[task_id]
        merged = current.model_copy(update=_coerce_patch(patch))
        merged.updated_at = to_iso(self.clock.utcnow())  # app-write marker (guard window)
        self.client.update_row(mapper.TAB_TASKS, row_number, mapper.serialize_task_row(merged))
        self.activity.append(
            employee_id=merged.created_by, task_id=task_id,
            activity_type=ActivityType.TASK_UPDATED,
            description=f"Updated fields {', '.join(sorted(patch.keys()))}.",
            source=source,
        )
        return merged

    # -- port: delete (physical + tombstone in Activity_Log) -----------------------
    def delete(self, task_id: str, *, source: RecordSource) -> bool:
        tasks, row_numbers, _ = self._load_all()
        current = next((t for t in tasks if t.task_id == task_id), None)
        if current is None:
            return False
        row_number = row_numbers[task_id]
        self.client.clear_row(mapper.TAB_TASKS, row_number)
        self.activity.append(
            employee_id=current.created_by, task_id=task_id,
            activity_type=ActivityType.TASK_DELETED,
            description=f"Deleted task '{current.title}'.",
            source=source,
        )
        return True


class SheetsReminderRepository:
    def __init__(
        self, client: Any, activity: SheetsActivityLogRepository,
        clock: Clock = DEFAULT_CLOCK,
    ) -> None:
        self.client = client
        self.activity = activity
        self.clock = clock

    def _load_all(self) -> tuple[dict[str, Reminder], dict[str, int]]:
        rows = self.client.get_rows(mapper.TAB_REMINDERS)
        reminders: dict[str, Reminder] = {}
        rows_idx: dict[str, int] = {}
        for idx, row in enumerate(rows, start=2):
            rem = mapper.parse_reminder_row(row)
            if rem is None:
                continue
            rows_idx[rem.reminder_id] = idx
            reminders[rem.reminder_id] = rem
        return reminders, rows_idx

    def create(
        self, *, task_id: str, employee_id: str, scheduled_at: str,
        source: RecordSource = RecordSource.API,
    ) -> Reminder:
        rem = Reminder(
            reminder_id=new_id("REM"), task_id=task_id, employee_id=employee_id,
            scheduled_at=scheduled_at, status=ReminderStatus.SCHEDULED,
            created_at=to_iso(self.clock.utcnow()),
        )
        self.client.append_row(mapper.TAB_REMINDERS, mapper.serialize_reminder_row(rem),
                               header=mapper._REMINDER_HEADER)
        self.activity.append(
            employee_id=employee_id, task_id=task_id,
            activity_type=ActivityType.REMINDER_SET,
            description=f"Scheduled reminder for {scheduled_at}.",
            source=source,
        )
        return rem

    def get(self, reminder_id: str) -> Reminder | None:
        return self._load_all()[0].get(reminder_id)

    def list(
        self, *, task_id: str | None = None, employee_id: str | None = None,
        status: ReminderStatus | None = None,
    ) -> list[Reminder]:
        items, _ = self._load_all()
        return [
            r for r in items.values()
            if (task_id is None or r.task_id == task_id)
            and (employee_id is None or r.employee_id == employee_id)
            and (status is None or r.status == status)
        ]

    def reschedule(self, reminder_id: str, scheduled_at: str) -> Reminder | None:
        items, rows = self._load_all()
        rem = items.get(reminder_id)
        if rem is None:
            return None
        merged = rem.model_copy(update={"scheduled_at": scheduled_at})
        self.client.update_row(
            mapper.TAB_REMINDERS, rows[reminder_id], mapper.serialize_reminder_row(merged),
        )
        return merged

    def update_status(self, reminder_id: str, status: ReminderStatus) -> Reminder | None:
        items, rows = self._load_all()
        rem = items.get(reminder_id)
        if rem is None:
            return None
        merged = rem.model_copy(update={"status": status})
        self.client.update_row(
            mapper.TAB_REMINDERS, rows[reminder_id], mapper.serialize_reminder_row(merged),
        )
        if status == ReminderStatus.SENT:
            self.activity.append(
                employee_id=merged.employee_id, task_id=merged.task_id,
                activity_type=ActivityType.REMINDER_SENT,
                description=f"Reminder sent (was scheduled for {merged.scheduled_at}).",
                source=RecordSource.API,
            )
        return merged


class SheetsCommandLogRepository:
    """Command_Log (T-062) — every chat turn + confirm/reject outcome is recorded."""

    def __init__(self, client: Any, clock: Clock = DEFAULT_CLOCK) -> None:
        self.client = client
        self.clock = clock

    def append(
        self, *, employee_id: str, conversation_id: str, raw_message: str,
        proposed_actions_count: int, command_status: str, timestamps: datetime | None = None,
    ) -> str:
        command_id = new_id("CMD")
        row = mapper.serialize_command_row(
            CommandLogEntry(
                command_id=command_id,
                timestamp=(to_iso(timestamps or self.clock.utcnow())),
                employee_id=employee_id,
                conversation_id=conversation_id,
                raw_message=raw_message,
                proposed_actions_count=proposed_actions_count,
                command_status=command_status,
                executed_action_ids="",
            )
        )
        self.client.append_row(mapper.TAB_COMMAND, row, header=mapper._COMMAND_HEADER)
        return command_id

    def update_status(self, command_id: str, command_status: str, executed_action_ids: str) -> None:
        rows = self.client.get_rows(mapper.TAB_COMMAND)
        for idx, row in enumerate(rows, start=2):
            if _cell0(row) == command_id:
                mutated = list(row)
                while len(mutated) < len(mapper._COMMAND_HEADER):
                    mutated.append("")
                mutated[6] = command_status                 # command_status column (index 6)
                mutated[7] = (executed_action_ids or "")    # executed_action_ids (index 7)
                self.client.update_row(mapper.TAB_COMMAND, idx, mutated)
                return


def _cell0(row: list[str]) -> str:
    if row:
        v = row[0]
        return "" if v is None else str(v).strip()
    return ""


def _coerce_patch(patch: dict[str, Any]) -> dict[str, Any]:
    """Coerce raw string values (agent payloads / manual patch dicts) into domain enums."""
    out: dict[str, Any] = {}
    for key, value in patch.items():
        if key == "status" and isinstance(value, str):
            value = TaskStatus(value.upper())
        elif key == "priority" and isinstance(value, str):
            value = Priority(value.upper())
        elif key == "source" and isinstance(value, str):
            value = RecordSource(value.upper())
        out[key] = value
    return out


def build_sheets_repositories(settings: Settings):
    """Ctor used by backend wiring (T-080) — config lives in Settings; no creds are touched here."""
    client = GoogleSheetsApiClient(settings)
    activity = SheetsActivityLogRepository(client)
    employees = SheetsEmployeeRepository(client)
    tasks = SheetsTaskRepository(client, employees, activity)
    reminders = SheetsReminderRepository(client, activity)
    commands = SheetsCommandLogRepository(client)
    return tasks, employees, activity, reminders, commands


__all__ = [
    "GoogleSheetsApiClient",
    "MemorySheetsClient",
    "SheetsActivityLogRepository",
    "SheetsCommandLogRepository",
    "SheetsEmployeeRepository",
    "SheetsReminderRepository",
    "SheetsTaskRepository",
    "build_sheets_repositories",
]
