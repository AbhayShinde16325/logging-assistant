"""Meeting extraction (T-102 pattern; P2 tier) — deterministic, contract-compliant MVP.

Contract: POST /api/v1/meetings/extract accepts pasted notes/transcript text only; returns a
summary, proposed actions (each confirmed INDIVIDUALLY via the standard confirm endpoint),
decisions and items. Heuristics are deliberately conservative: they never invent employees or
dates (name matching runs through the same resolution as chat).
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.models.domain import ActivityType, Employee, RecordSource
from backend.app.services.action_store import ActionStore
from backend.app.services.ports import (
    ActivityLogRepository,
    EmployeeRepository,
    TaskRepository,
)
from agent.app.nodes import resolution
from backend.app.utils.errors import validation_error
from backend.app.utils.ids import Clock, new_id, to_iso

ACTION_ITEM_PAT = re.compile(
    r"^\s*(?:[-*•]|\((\d)\))?\s*(?:f?\[ \])?\s*(?P<text>.+)$",
)
DECISION_PAT = re.compile(r"\bdecid(?:ed|e[sd]?)\b|\bdecision\b|\bagreed\b|\blive with\b", re.I)
ASSIGNEE_PAT = re.compile(r"\b(?:@|assign(?:ed)? to|owner:)\s*(?P<name>[A-Za-z]+)", re.I)
DUE_PAT = re.compile(r"\bby\s+(?P<when>[A-Za-z]+ ?\d{0,2}(?:st|nd|rd|th)?|tomorrow|next \w+)\b", re.I)


class MeetingService:
    def __init__(
        self,
        tasks: TaskRepository,
        employees: EmployeeRepository,
        activity: ActivityLogRepository,
        actions: ActionStore,
        clock: Clock,
    ) -> None:
        self.tasks = tasks
        self.employees = employees
        self.activity = activity
        self.actions = actions
        self.clock = clock
        self.employees_map = {e.name.lower(): e for e in employees.list()}

    def extract(self, text: str, *, employee_id: str, date: str | None = None,
                title: str | None = None) -> dict[str, Any]:
        lines = [l.rstrip() for l in text.splitlines() if l.strip()]
        if not lines:
            raise validation_error("Meeting text must not be empty.")

        summary = title or lines[0][:200]
        decisions: list[str] = []
        items: list[str] = []
        candidates: list[dict[str, str | None]] = []

        for line in lines:
            m = ACTION_ITEM_PAT.match(line)
            body = (m.group("text") if m else line).strip()
            if not body:
                continue
            if DECISION_PAT.search(body):
                decisions.append(body[:300])
                continue
            if _looks_like_action(body):
                items.append(body[:300])
                candidates.append(body)

        # resolve people/dates for action items -> CREATE_TASK proposals
        now = self.clock.utcnow()
        today = now.date()
        base_date: date | None = None
        if date:
            try:
                from datetime import date as _date

                y, mo, dd = (int(v) for v in date.split("-"))
                base_date = _date(y, mo, dd)
            except ValueError:
                raise validation_error("date must be YYYY-MM-DD", {"date": date})
        today = base_date or today

        employees_alert: list[str] = []
        proposed_payloads: list[dict[str, Any]] = []
        for body in candidates[:5]:
            due = None
            assignee_id: str | None = None
            assignee_is_me = False
            dm = DUE_PAT.search(body)
            if dm:
                resolved = resolution.resolve_due_date(dm.group("when"), today)
                if not resolved.needs_clarification:
                    due = resolved.due_date
            am = ASSIGNEE_PAT.search(body)
            if am:
                name = am.group("name").lower()
                emp = self.employees_map.get(name)
                if emp is not None:
                    assignee_id = emp.employee_id
                else:
                    employees_alert.append(am.group("name"))
            if not re.search(r"\b(i|my|me)\b", body.lower()) and not assignee_id:
                assignee_id = employee_id
                assignee_is_me = True
            elif re.search(r"^i\b|\bmy\b", body.lower()):
                assignee_id, assignee_is_me = employee_id, True
            clean_title = body
            clean_title = re.sub(r"^action item[:\-]?\s*", "", clean_title, flags=re.I)[:140]
            proposed_payloads.append(
                {
                    "title": clean_title,
                    "description": body[:1000],
                    "assignee_id": assignee_id,
                    "due_date": due,
                    "priority": "MEDIUM",
                }
            )

        # persist pending actions (same lifecycle as chat proposals)
        from backend.app.models.domain import ActionStatus, ActionType, ProposedAction

        now_iso = to_iso(now)
        conv = new_id("CONV")
        proposed_actions: list[dict[str, Any]] = []
        for payload in proposed_payloads:
            a = ProposedAction(
                action_id=new_id("ACT"),
                conversation_id=conv,
                action_type=ActionType.CREATE_TASK,
                payload=payload,
                status=ActionStatus.PENDING,
                created_at=now_iso,
            )
            self.actions.add(a, requester_id=employee_id, command_id=None)
            proposed_actions.append(
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type.value,
                    "payload": a.payload,
                    "status": a.status.value,
                }
            )

        self.activity.append(
            employee_id=employee_id,
            task_id=None,
            activity_type=ActivityType.MEETING_EXTRACTED,
            description=f"Extracted {len(proposed_payloads)} action item(s) from notes"
            + (f" '{summary[:80]}'" if summary else ""),
            source=RecordSource.MEETING,
        )
        return {
            "summary": summary,
            "proposed_actions": proposed_actions,
            "requires_confirmation": bool(proposed_actions),
            "decisions": decisions,
            "items": items,
        }


class _mk_action_result:
    """Local struct used to synthesize ProposedActions deterministically (docs §8 workflows)."""

    def __init__(self, action_id: str, payload: dict[str, Any]) -> None:
        self.action_id = action_id
        self.payload = payload


def _looks_like_action(body: str) -> bool:
    verbs = (
        "assign", "send", "prepare", "research", "write", "review", "follow up", "schedule",
        "create", "update", "document", "implement", "test", "fix", "ship", "check", "finish",
        "complete", "plan",
    )
    lower = body.lower()
    return any(v in lower for v in verbs) and bool(
        DUE_PAT.search(body) or re.search(r"^[-*•]", body)
    )
