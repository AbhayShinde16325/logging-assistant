"""Chat orchestration (tasks T-050/T-053/T-080): route ↔ agent graph ↔ ports.

The backend owns: validation, Command_Log writing, pending-action persistence, and read-only
query answering. The agent graph proposes; only /actions/{id}/confirm (ActionService) executes.
"""

from __future__ import annotations

import re
from datetime import timedelta
from typing import Any

from backend.app.models.domain import (
    Priority,
    ProposedAction,
    RecordSource,
    TaskStatus,
)
from backend.app.services.action_store import ActionStore
from backend.app.services.memory import MemoryActivityLogRepository
from backend.app.services.ports import (
    ActivityLogRepository,
    CommandLogRepository,
    EmployeeRepository,
    TaskRepository,
)
from backend.app.utils.ids import Clock
from backend.app.utils.errors import validation_error
from backend.app.utils.ids import new_id, to_iso

from agent.app.graph import AgentContext, AgentGraph
from agent.app.state import Intent


class ChatService:
    def __init__(
        self,
        graph: AgentGraph,
        tasks: TaskRepository,
        employees: EmployeeRepository,
        activity: ActivityLogRepository,
        commands: CommandLogRepository,
        action_store: ActionStore,
        clock: Clock,
    ) -> None:
        self.graph = graph
        self.tasks = tasks
        self.employees = employees
        self.activity = activity
        self.commands = commands
        self.actions = action_store
        self.clock = clock

    # ------------------------------------------------------------------ helpers
    def _resolve_caller(self, employee_id: str | None) -> str:
        employees = self.employees.list()
        if employee_id:
            if self.employees.get(employee_id) is None:
                raise validation_error(
                    f"Unknown employee '{employee_id}'. Employees live in the sheet's Employees tab.",
                    {"employee_id": employee_id},
                )
            return employee_id
        if len(employees) == 1:
            return employees[0].employee_id
        raise validation_error(
            "employee_id is required when more than one employee exists in the sheet.",
            {"known_employees": [e.employee_id for e in employees]},
        )

    def _task_lookup(
        self, *, title_contains: str | None = None, assignee_id: str | None = None,
    ) -> list[dict[str, Any]]:
        title = title_contains
        if title:
            # tolerate leading articles ("remind me about the quarterly report")
            needle = " ".join(title.strip().lower().split())
            needle = re.sub(r"^(the|a|an)\s+", "", needle)
            title = needle
        if title_contains is None and assignee_id is None:
            items, _ = self.tasks.list_tasks(limit=20)
        else:
            items, _ = self.tasks.list_tasks(title_contains=title, assignee_id=assignee_id)
        return [t.model_dump(mode="json") for t in items]

    def _pending_task_summary(self, employee_id: str) -> list[dict[str, Any]]:
        items, _ = self.tasks.list_tasks(
            assignee_id=employee_id, status=TaskStatus.TODO,
        )
        items2, total = self.tasks.list_tasks(assignee_id=employee_id)
        open_items = [t for t in items2 if t.status in
                      (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)]
        return {"total_open": len(open_items), "tasks": [t.model_dump(mode="json") for t in items]}

    # ------------------------------------------------------------------ main flow
    def chat(
        self, message: str, *, employee_id: str | None = None,
        conversation_id: str | None = None, source: str = "CHAT",
    ) -> dict[str, Any]:
        caller = self._resolve_caller(employee_id)
        conv = conversation_id or new_id("CONV")
        row = self.commands.append(
            employee_id=caller,
            conversation_id=conv,
            raw_message=message,
            proposed_actions_count=0,
            command_status="PENDING",
            timestamps=None,
        )
        ctx = AgentContext(
            employee_id=caller,
            employees=self.employees.list(),
            clock=self.clock,
            task_lookup=self._task_lookup,
            source=source,
        )
        now_iso = to_iso(self.clock.utcnow())
        result = self.graph.run(
            {
                "raw_input": message,
                "normalized_input": "",
                "language": "en",
                "employee_id": caller,
                "intent": "",
                "entities": {},
                "proposed_actions": [],
                "validation_issues": [],
                "source": source,
            },
            ctx,
        )

        intent = Intent(result.get("intent", Intent.UNKNOWN))
        proposed_out: list[ProposedAction] = []
        stored_payloads: list[dict[str, Any]] = []
        for p in result.get("proposed_actions", []):
            a = ProposedAction(
                action_id=p["action_id"],
                conversation_id=conv,
                action_type=p["action_type"],
                payload=p["payload"],
                status="PENDING",
                created_at=now_iso,
            )
            self.actions.add(a, requester_id=caller, command_id=row)
            proposed_out.append(a)
            stored_payloads.append(
                {"action_id": a.action_id, "action_type": a.action_type.value, "payload": a.payload}
            )

        self.commands.update_status(row, "PROPOSED" if proposed_out else "LOGGED", "")

        # read-only queries answered from the ports (never from model memory)
        inline_result: dict[str, Any] | None = None
        reply = result.get("system_reply", "")
        requires = result.get("requires_confirmation", False)
        if intent is Intent.QUERY_TASKS:
            inline_result = self._pending_task_summary(caller)
            tasks = inline_result["tasks"]
            if tasks:
                reply = (
                    f"You have {inline_result['total_open']} open task(s). "
                    + "; ".join(
                        f"{t['task_id']} '{t['title']}' (due {t.get('due_date')})"
                        for t in tasks[:5]
                    )
                )
            else:
                reply = "You have no pending tasks."
        elif intent is Intent.QUERY_ACTIVITY:
            since = self.clock.utcnow() - timedelta(days=7)
            entries, total = self.activity.list(employee_id=caller, limit=20)
            recent = [e for e in entries if e.timestamp >= to_iso(since)]
            inline_result = {"total": len(recent), "entries": [e.model_dump(mode="json") for e in recent]}
            reply = (
                f"Recent activity ({len(recent)} items this week): "
                + "; ".join(e.description for e in recent[:5])
                if recent else "No recent activity logged."
            )
        if not reply:
            reply = "I couldn't fully process that. Could you rephrase it?"

        self.commands.update_status(row, "PROPOSED" if proposed_out else "LOGGED", "")
        return {
            "conversation_id": conv,
            "message": reply,
            "requires_confirmation": requires,
            "proposed_actions": [
                {"action_id": a.action_id, "action_type": a.action_type, "payload": a.payload,
                 "status": "PENDING"}
                for a in proposed_out
            ],
            "result": inline_result,
        }
