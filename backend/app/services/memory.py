"""In-memory implementations of the ports (task T-012).

Used by unit/contract tests and the *dev fallback* when Google Sheets is not configured
(ADR-002: storage is swappable — these never pretend to be Sheets; health reports
`google_sheets: unavailable` in this mode). Behavior deliberately mirrors the Sheets repositories:
every mutation appends an Activity_Log entry, ownership of records logged with source.
"""

from __future__ import annotations

from datetime import datetime
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
from backend.app.services.ports import ServiceDefaults
from backend.app.utils.ids import DEFAULT_CLOCK, Clock, new_id
from backend.app.utils.ids import to_iso


class MemoryEmployeeRepository:
    def __init__(self, employees: list[Employee] | None = None) -> None:
        self._employees: dict[str, Employee] = {e.employee_id: e for e in (employees or [])}

    def add(self, employee: Employee) -> None:
        self._employees[employee.employee_id] = employee

    def list(self) -> list[Employee]:
        return list(self._employees.values())

    def get(self, employee_id: str) -> Employee | None:
        return self._employees.get(employee_id)


class MemoryActivityLogRepository:
    def __init__(self, clock: Clock = DEFAULT_CLOCK) -> None:
        self._entries: list[ActivityEntry] = []
        self.clock = clock

    def append(
        self, *, employee_id: str, task_id: str | None, activity_type: ActivityType,
        description: str, source: RecordSource, timestamp: datetime | None = None,
    ) -> ActivityEntry:
        entry = ActivityEntry(
            activity_id=new_id("LOG"),
            employee_id=employee_id,
            task_id=task_id,
            activity_type=activity_type,
            description=description[:500],
            timestamp=to_iso(timestamp or self.clock.utcnow()),
            source=source,
        )
        self._entries.append(entry)
        return entry

    def list(
        self, *, employee_id: str | None = None, task_id: str | None = None,
        limit: int = 200, offset: int = 0,
    ) -> tuple[list[ActivityEntry], int]:
        items = [
            e for e in self._entries
            if (employee_id is None or e.employee_id == employee_id)
            and (task_id is None or e.task_id == task_id)
        ]
        total = len(items)
        return items[offset:offset + limit], total


class MemoryTaskRepository:
    def __init__(self, employees: MemoryEmployeeRepository, activity: MemoryActivityLogRepository,
                 clock: Clock = DEFAULT_CLOCK) -> None:
        self._tasks: dict[str, Task] = {}
        self.employees = employees
        self.activity = activity
        self.clock = clock

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _norm_title(title: str) -> str:
        return " ".join(title.lower().split())

    # -- port methods --------------------------------------------------------
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
            description=(description or None),
            assignee_id=assignee_id,
            created_by=created_by,
            status=status,
            priority=priority,
            due_date=due_date,
            created_at=now,
            updated_at=now,
            source=source,
            external_reference=external_reference,
        )
        self._tasks[task.task_id] = task
        self.activity.append(
            employee_id=created_by, task_id=task.task_id,
            activity_type=ActivityType.TASK_CREATED,
            description=f"Created task '{task.title}' (assignee {assignee_id}).",
            source=source,
        )
        return task

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list_tasks(
        self, *, assignee_id: str | None = None, status: TaskStatus | None = None,
        title_contains: str | None = None, due_before: str | None = None,
        due_after: str | None = None, limit: int = 200, offset: int = 0,
    ) -> tuple[list[Task], int]:
        needles = self._norm_title(title_contains) if title_contains else None
        items = []
        for t in self._tasks.values():
            if assignee_id is not None and t.assignee_id != assignee_id:
                continue
            if status is not None and t.status != status:
                continue
            if needles and needles not in self._norm_title(t.title):
                continue
            if due_before and not (t.due_date and t.due_date <= due_before):
                continue
            if due_after and not (t.due_date and t.due_date >= due_after):
                continue
            items.append(t)
        # sort by due_date ascending; None due_dates last; then created_at asc
        items.sort(key=lambda t: (t.due_date or "9999-12-31", t.created_at))
        total = len(items)
        return items[offset:offset + limit], total

    def find_open_duplicate(self, assignee_id: str, title: str) -> Task | None:
        needle = self._norm_title(title)
        for t in self._tasks.values():
            if t.assignee_id == assignee_id and t.status in ServiceDefaults.OPEN_STATUSES:
                if self._norm_title(t.title) == needle:
                    return t
        return None

    def update(
        self, task_id: str, patch: dict[str, Any], *, source: RecordSource,
    ) -> Task | None:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        changes = dict(patch)
        task = task.model_copy(update=changes)
        task.updated_at = to_iso(self.clock.utcnow())
        self._tasks[task_id] = task
        self.activity.append(
            employee_id=task.created_by, task_id=task_id,
            activity_type=ActivityType.TASK_UPDATED,
            description=f"Updated task {','.join(sorted(changes.keys()))}.",
            source=source,
        )
        return task

    def delete(self, task_id: str, *, source: RecordSource) -> bool:
        task = self._tasks.pop(task_id, None)
        if task is None:
            return False
        self.activity.append(
            employee_id=task.created_by, task_id=task_id,
            activity_type=ActivityType.TASK_DELETED,
            description=f"Deleted task '{task.title}'.",
            source=source,
        )
        return True


class MemoryReminderRepository:
    def __init__(self, employees: MemoryEmployeeRepository, activity: MemoryActivityLogRepository,
                 clock: Clock = DEFAULT_CLOCK) -> None:
        self._reminders: dict[str, Reminder] = {}
        self.employees = employees
        self.activity = activity
        self.clock = clock

    def create(
        self, *, task_id: str, employee_id: str, scheduled_at: str,
        source: RecordSource = RecordSource.API,
    ) -> Reminder:
        r = Reminder(
            reminder_id=new_id("REM"),
            task_id=task_id,
            employee_id=employee_id,
            scheduled_at=scheduled_at,
            status=ReminderStatus.SCHEDULED,
            created_at=to_iso(self.clock.utcnow()),
        )
        self._reminders[r.reminder_id] = r
        self.activity.append(
            employee_id=employee_id, task_id=task_id,
            activity_type=ActivityType.REMINDER_SET,
            description=f"Scheduled reminder for {scheduled_at}.",
            source=source,
        )
        return r

    def get(self, reminder_id: str) -> Reminder | None:
        return self._reminders.get(reminder_id)

    def list(
        self, *, task_id: str | None = None, employee_id: str | None = None,
        status: ReminderStatus | None = None,
    ) -> list[Reminder]:
        return [
            r for r in self._reminders.values()
            if (task_id is None or r.task_id == task_id)
            and (employee_id is None or r.employee_id == employee_id)
            and (status is None or r.status == status)
        ]

    def reschedule(self, reminder_id: str, scheduled_at: str) -> Reminder | None:
        r = self._reminders.get(reminder_id)
        if r is None:
            return None
        updated = r.model_copy(update={"scheduled_at": scheduled_at})
        self._reminders[reminder_id] = updated
        return updated

    def update_status(self, reminder_id: str, status: ReminderStatus) -> Reminder | None:
        r = self._reminders.get(reminder_id)
        if r is None:
            return None
        r = r.model_copy(update={"status": status})
        self._reminders[reminder_id] = r
        if status == ReminderStatus.SENT:
            self.activity.append(
                employee_id=r.employee_id, task_id=r.task_id,
                activity_type=ActivityType.REMINDER_SENT,
                description=f"Reminder sent (was scheduled for {r.scheduled_at}).",
                source=RecordSource.API,
            )
        return r

    def all_for_clock_check(self) -> list[Reminder]:
        return list(self._reminders.values())


class MemoryCommandLogRepository:
    def __init__(self, clock: Clock = DEFAULT_CLOCK) -> None:
        self._commands: dict[str, CommandLogEntry] = {}
        self.clock = clock

    def append(
        self, *, employee_id: str, conversation_id: str, raw_message: str,
        proposed_actions_count: int, command_status: str, timestamps: datetime | None = None,
    ) -> str:
        cid = new_id("CMD")
        self._commands[cid] = CommandLogEntry(
            command_id=cid,
            timestamp=to_iso(timestamps or self.clock.utcnow()),
            employee_id=employee_id,
            conversation_id=conversation_id,
            raw_message=raw_message,
            proposed_actions_count=proposed_actions_count,
            command_status=command_status,
            executed_action_ids="",
        )
        return cid

    def update_status(self, command_id: str, command_status: str, executed_action_ids: str) -> None:
        c = self._commands.get(command_id)
        if c is not None:
            self._commands[command_id] = c.model_copy(
                update={
                    "command_status": command_status,
                    "executed_action_ids": (executed_action_ids or "").strip("'"),
                }
            )
