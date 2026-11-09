"""API schemas (T-011) — Pydantic mirrors of ../..../contracts/*.schema.json.

Mapping table: contracts/README.md. Field-level changes require the coordinated contracts PR.
Request schemas use strict extra='forbid'; response schemas serialize exactly like the contract.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.domain import (
    ActionStatus,
    ActionType,
    ActivityEntry,
    ActivityType,
    Employee,
    Priority,
    ProposedAction,
    RecordSource,
    Reminder,
    ReminderStatus,
    Task,
    TaskStatus,
)

ID_PATTERN = Field(pattern=r"^(TASK|EMP|REM|ACT|LOG|CONV|CMD)-[0-9a-f]{8}$")
EMP_PATTERN = Field(pattern=r"^EMP-[0-9]{3,}$")
TASK_PATTERN = Field(pattern=r"^TASK-[0-9a-f]{8}$")
REM_PATTERN = Field(pattern=r"^REM-[0-9a-f]{8}$")
ACT_PATTERN = Field(pattern=r"^ACT-[0-9a-f]{8}$")
CONV_PATTERN = Field(pattern=r"^CONV-[0-9a-f]{8}$")
DATE_PATTERN = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")

# raw pattern strings reused by Optional[...] fields (FieldInfo objects aren't callable)
EMP_STRING_RE = r"^EMP-[0-9]{3,}$"
CONV_STRING_RE = r"^CONV-[0-9a-f]{8}$"
TASK_STRING_RE = r"^TASK-[0-9a-f]{8}$"
DATE_STRING_RE = r"^\d{4}-\d{2}-\d{2}$"


# ---- Health --------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    version: str
    components: dict[str, str]


# ---- Chat ----------------------------------------------------------------
class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=2000)
    employee_id: str | None = Field(default=None, pattern=EMP_STRING_RE)
    conversation_id: str | None = Field(default=None, pattern=CONV_STRING_RE)


class ProposedActionOut(BaseModel):
    action_id: str
    action_type: ActionType
    payload: dict[str, Any]
    status: ActionStatus = ActionStatus.PENDING

    @classmethod
    def of(cls, action: ProposedAction) -> "ProposedActionOut":
        return cls(
            action_id=action.action_id,
            action_type=action.action_type,
            payload=action.payload,
            status=action.status,
        )


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    requires_confirmation: bool
    proposed_actions: list[ProposedActionOut] = []
    result: dict[str, Any] | None = None


# ---- Actions (confirm/reject) ---------------------------------------------
class ConfirmResponse(BaseModel):
    status: str
    action_id: str
    result: dict[str, Any] | None = None


class RejectResponse(BaseModel):
    status: str
    action_id: str


# ---- Tasks ------------------------------------------------------------------
class TaskCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=140)
    description: str | None = None
    assignee_id: str = EMP_PATTERN
    status: TaskStatus = TaskStatus.TODO
    priority: Priority = Priority.MEDIUM
    due_date: str | None = Field(default=None, pattern=DATE_STRING_RE)
    source: RecordSource = RecordSource.API
    external_reference: str | None = None


class TaskPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(None, min_length=1, max_length=140)
    description: str | None = None
    assignee_id: str | None = Field(default=None, pattern=EMP_STRING_RE)
    status: TaskStatus | None = None
    priority: Priority | None = None
    due_date: str | None = Field(default=None, pattern=DATE_STRING_RE)

    @model_validator(mode="after")
    def at_least_one_field(self) -> "TaskPatchIn":
        if all(
            getattr(self, f) is None
            for f in ("title", "description", "assignee_id", "status", "priority", "due_date")
        ):
            raise ValueError("At least one field must be provided")
        return self


class TaskOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    title: str
    description: str | None
    assignee_id: str
    created_by: str
    status: TaskStatus
    priority: Priority
    due_date: str | None
    created_at: str
    updated_at: str
    source: RecordSource
    external_reference: str | None

    @classmethod
    def of(cls, t: Task) -> "TaskOut":
        return cls(**t.model_dump())


class TaskListResponse(BaseModel):
    tasks: list[TaskOut]
    total: int


class TaskSingleResponse(BaseModel):
    task: TaskOut


# ---- Employees ---------------------------------------------------------
class EmployeeOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str
    name: str
    email: str
    role: str
    created_at: str

    @classmethod
    def of(cls, e: Employee) -> "EmployeeOut":
        return cls(**e.model_dump())


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeOut]


# ---- Activity -----------------------------------------------------------
class ActivityEntryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_id: str
    employee_id: str
    task_id: str | None
    activity_type: ActivityType
    description: str
    timestamp: str
    source: RecordSource

    @classmethod
    def of(cls, e: ActivityEntry) -> "ActivityEntryOut":
        return cls(**e.model_dump())


class ActivityListResponse(BaseModel):
    activity: list[ActivityEntryOut]
    total: int


class ActivityCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str = EMP_PATTERN
    task_id: str | None = Field(default=None, pattern=TASK_STRING_RE)
    activity_type: ActivityType
    description: str = Field(min_length=1, max_length=500)
    source: RecordSource


# ---- Voice ------------------------------------------------------------
class TranscribeResponse(BaseModel):
    transcription: str
    confidence: float = Field(ge=0, le=1)
    provider: str


# ---- Dashboard --------------------------------------------------------
class DashboardEmployeeSummary(BaseModel):
    employee_id: str
    name: str
    open_tasks: int
    overdue: int
    completed_7d: int


class DashboardSummary(BaseModel):
    team: dict[str, Any]
    employees: list[DashboardEmployeeSummary]


# ---- Meetings --------------------------------------------------------
class MeetingExtractIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    employee_id: str = EMP_PATTERN
    text: str = Field(min_length=1, max_length=20000)
    date: str | None = Field(default=None, pattern=DATE_STRING_RE)


class MeetingExtractResponse(BaseModel):
    summary: str | None
    proposed_actions: list[ProposedActionOut]
    requires_confirmation: bool
    decisions: list[str]
    items: list[str]


# ---- Reminders --------------------------------------------------------
class ReminderCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = TASK_PATTERN
    employee_id: str = EMP_PATTERN
    scheduled_at: str


class ReminderPatchIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scheduled_at: str | None = None
    status: ReminderStatus | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "ReminderPatchIn":
        if self.scheduled_at is None and self.status is None:
            raise ValueError("At least one field must be provided")
        return self


class ReminderCreateOut(BaseModel):
    reminder_id: str
    task_id: str
    employee_id: str
    scheduled_at: str
    status: ReminderStatus
    created_at: str

    @classmethod
    def of(cls, r: Reminder) -> "ReminderCreateOut":
        return cls(**r.model_dump())


class ReminderListResponse(BaseModel):
    reminders: list[ReminderCreateOut]
