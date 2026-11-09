"""Confirm/reject — the ONLY path that executes proposed actions (tasks T-052, T-053).

Re-validates against current repository state at execution time (docs/api-contracts.md):
- The LLM never writes; this backend-owned service dispatches the validated payload to ports.
- Re-validation failures (validation_error/not_found) leave the action PENDING (422/404).
- Integration failures leave the action PENDING (502) so the user can retry after fixing state.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.models.domain import (
    ActionStatus,
    ActionType,
    ActivityType,
    ProposedAction,
    RecordSource,
    TaskStatus,
)
from backend.app.services.action_store import ActionStore
from backend.app.services.ports import (
    ActivityLogRepository,
    CommandLogRepository,
    EmployeeRepository,
    ReminderRepository,
    TaskRepository,
)
from backend.app.services.task_service import TaskService
from backend.app.utils.errors import (
    ApiError,
    ErrorCode,
    action_not_pending,
    integration_error,
    not_found,
    validation_error,
)

logger = logging.getLogger(__name__)


class ActionExecutionResult:
    def __init__(self, summary: dict[str, Any]) -> None:
        self.summary = summary


class ActionService:
    def __init__(
        self,
        action_store: ActionStore,
        tasks: TaskRepository,
        employees: EmployeeRepository,
        reminders: ReminderRepository,
        activity: ActivityLogRepository,
        commands: CommandLogRepository,
    ) -> None:
        self.store = action_store
        self.tasks = tasks
        self.employees = employees
        self.reminders = reminders
        self.activity = activity
        self.commands = commands
        self.task_service = TaskService(tasks, employees)

    # -- confirm ---------------------------------------------------------
    def confirm(self, action_id: str) -> ActionExecutionResult:
        action = self._pending(action_id)
        requester_id, command_id = self.store.binding(action.action_id)
        try:
            result = self._execute(action, requester_id)
        except ApiError as err:
            if err.code in (ErrorCode.VALIDATION_ERROR, ErrorCode.NOT_FOUND):
                raise  # stays PENDING per api-contracts.md
            raise integration_error(
                f"Execution failed for action {action.action_id}: {err.message}",
                {"action_id": action.action_id},
            ) from err
        except Exception as err:  # unexpected failure — surface as integration error, stay pending
            logger.exception("Unexpected failure executing action %s", action.action_id)
            raise integration_error(
                f"Execution failed for action {action.action_id}.",
                {"action_id": action.action_id},
            ) from err
        self.store.mark(action.action_id, ActionStatus.EXECUTED)
        if command_id:
            self.commands.update_status(command_id, "CONFIRMED", action.action_id)
        return ActionExecutionResult(result)

    def reject(self, action_id: str) -> ProposedAction:
        action = self._pending(action_id)
        rejected = self.store.mark(action.action_id, ActionStatus.REJECTED)
        _, command_id = self.store.binding(action.action_id)
        if command_id:
            self.commands.update_status(command_id, "REJECTED", action.action_id)
        return rejected

    def _pending(self, action_id: str) -> ProposedAction:
        action = self.store.get(action_id)
        if action is None:
            raise not_found(f"Action '{action_id}' not found.", {"action_id": action_id})
        if action.status != ActionStatus.PENDING:
            raise action_not_pending(
                f"Action '{action_id}' is {action.status.value} and cannot be processed again.",
                {"action_id": action_id, "status": action.status.value},
            )
        return action

    # -- dispatch (single validation + execution point) --------------------
    def _execute(self, action: ProposedAction, requester_id: str | None) -> dict[str, Any]:
        kind = action.action_type
        payload = action.payload
        if kind is ActionType.CREATE_TASK:
            return self._create_task(payload, requester_id)
        if kind is ActionType.UPDATE_TASK:
            return self._update_task(payload)
        if kind is ActionType.COMPLETE_TASK:
            return self._complete_task(payload)
        if kind is ActionType.ASSIGN_TASK:
            return self._assign_task(payload)
        if kind is ActionType.DELETE_TASK:
            return self._delete_task(payload)
        if kind is ActionType.CREATE_REMINDER:
            return self._create_reminder(payload)
        raise validation_error(f"Unsupported action type {kind}.", {"action_type": kind.value})

    def _create_task(self, payload: dict[str, Any], requester_id: str | None) -> dict[str, Any]:
        task = self.task_service.create_task(
            title=payload["title"],
            assignee_id=payload["assignee_id"],
            created_by=requester_id or payload["assignee_id"],
            description=payload.get("description"),
            priority=payload.get("priority") or "MEDIUM",
            due_date=payload.get("due_date"),
            source=RecordSource.CHAT,
        )
        return {"task": task.model_dump(mode="json")}

    def _update_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        patch: dict[str, Any] = {}
        for field in ("title", "description", "assignee_id", "status", "priority", "due_date"):
            if payload.get(field) is not None:
                patch[field] = payload[field]
        task = self.task_service.patch_task(payload["task_id"], patch, source=RecordSource.CHAT)
        return {"task": task.model_dump(mode="json")}

    def _complete_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self.task_service.patch_task(
            payload["task_id"],
            {"status": TaskStatus.DONE},
            source=RecordSource.CHAT,
        )
        self.activity.append(
            employee_id=task.created_by,
            task_id=task.task_id,
            activity_type=ActivityType.TASK_COMPLETED,
            description="Marked task completed via chat."
            + (f" Note: {payload.get('comment')}" if payload.get("comment") else ""),
            source=RecordSource.CHAT,
        )
        return {"task": task.model_dump(mode="json")}

    def _assign_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "task_id" not in payload:
            # New task phrased as "assign X to Y": creation + assignment in one step.
            return self._create_task(payload, requester_id=payload.get("assignee_id"))
        task = self.task_service.patch_task(
            payload["task_id"], {"assignee_id": payload["assignee_id"]}, source=RecordSource.CHAT,
        )
        return {"task": task.model_dump(mode="json")}

    def _delete_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.task_service.delete_task(payload["task_id"], source=RecordSource.CHAT)
        return {"task_id": payload["task_id"]}

    def _create_reminder(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.task_service.validate_employees_exist(payload["employee_id"])
        self.task_service.get_task(payload["task_id"])  # FK existence at execution time
        reminder = self.reminders.create(
            task_id=payload["task_id"],
            employee_id=payload["employee_id"],
            scheduled_at=payload["scheduled_at"],
            source=RecordSource.CHAT,
        )
        return {"reminder": reminder.model_dump(mode="json")}
