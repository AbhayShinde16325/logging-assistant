"""Domain models (docs/data-model.md). Pydantic v2; used across services, repositories and routes.

Field definitions follow contracts/*.schema.json — changing a field here requires the coordinated
contracts PR (JSON Schema + Pydantic + TypeScript together).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


class Priority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RecordSource(StrEnum):
    CHAT = "CHAT"
    VOICE = "VOICE"
    MEETING = "MEETING"
    MANUAL_SHEET = "MANUAL_SHEET"
    API = "API"


class ActionType(StrEnum):
    CREATE_TASK = "CREATE_TASK"
    UPDATE_TASK = "UPDATE_TASK"
    DELETE_TASK = "DELETE_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"
    ASSIGN_TASK = "ASSIGN_TASK"
    CREATE_REMINDER = "CREATE_REMINDER"
    QUERY = "QUERY"


class ActionStatus(StrEnum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ActivityType(StrEnum):
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_DELETED = "TASK_DELETED"
    TASK_COMPLETED = "TASK_COMPLETED"
    REMINDER_SET = "REMINDER_SET"
    REMINDER_SENT = "REMINDER_SENT"
    MEETING_EXTRACTED = "MEETING_EXTRACTED"
    MANUAL_SHEET_EDIT = "MANUAL_SHEET_EDIT"
    NOTE_SUBMITTED = "NOTE_SUBMITTED"


class ReminderStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    DUE = "DUE"
    SENT = "SENT"
    CANCELLED = "CANCELLED"


class Employee(BaseModel):
    employee_id: str = Field(pattern=r"^EMP-[0-9]{3,}$")
    name: str
    email: str
    role: str
    created_at: str


class Task(BaseModel):
    task_id: str = Field(pattern=r"^TASK-[0-9a-f]{8}$")
    title: str = Field(min_length=1, max_length=140)
    description: str | None = None
    assignee_id: str = Field(pattern=r"^EMP-[0-9]{3,}$")
    created_by: str = Field(pattern=r"^EMP-[0-9]{3,}$")
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    due_date: str | None = None
    created_at: str
    updated_at: str
    source: RecordSource = RecordSource.API
    external_reference: str | None = None


class ActivityEntry(BaseModel):
    activity_id: str = Field(pattern=r"^LOG-[0-9a-f]{8}$")
    employee_id: str
    task_id: str | None = None
    activity_type: ActivityType
    description: str = Field(max_length=500)
    timestamp: str
    source: RecordSource


class Reminder(BaseModel):
    reminder_id: str = Field(pattern=r"^REM-[0-9a-f]{8}$")
    task_id: str = Field(pattern=r"^TASK-[0-9a-f]{8}$")
    employee_id: str
    scheduled_at: str  # ISO 8601 UTC
    status: ReminderStatus = ReminderStatus.SCHEDULED
    created_at: str


class ProposedAction(BaseModel):
    """The agent's proposal — the ONLY thing the LLM path may contribute (contract: agent-action)."""

    action_id: str = Field(pattern=r"^ACT-[0-9a-f]{8}$")
    conversation_id: str | None = None
    action_type: ActionType
    payload: dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING
    created_at: str | None = None
    executed_at: str | None = None


class CommandLogEntry(BaseModel):
    """docs/data-model.md — Command_Log stores commands + proposed/executed actions."""

    command_id: str = Field(pattern=r"^CMD-[0-9a-f]{8}$")
    timestamp: str
    employee_id: str
    conversation_id: str
    raw_message: str
    proposed_actions_count: int
    command_status: str  # PROPOSED | CONFIRMED | REJECTED | FAILED | EXPIRED
    executed_action_ids: str
