"""LangGraph assembly (task T-013) — docs/agent-workflow.md §1/§3, ADR-003.

Node chain (per chat turn):
    normalize → classify → extract → resolve_employees → resolve_dates → validate_and_propose → compose_reply

Hard rules (agent/AGENTS.md):
- Nodes are pure: no network, no repository writes. Read-only lookups come from the backend through
  `AgentContext` (task_lookup / employees snapshot / clock).
- LLM output is parsed with Pydantic; provider-unavailable or unparseable output falls back to the
  deterministic heuristics (nodes/heuristics.py) — graceful clarification, never fabrication.
- The graph produces ProposedActions (contracts/agent-action.schema.json) only; it never executes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel, Field, ValidationError

from agent.app.models.providers import ModelProvider, ProviderUnavailableError
from agent.app.nodes import heuristics, resolution
from agent.app.prompts.templates import (
    EXTRACT_SYSTEM_PROMPT,
    INTENT_SYSTEM_PROMPT,
    extraction_user_prompt,
    intent_user_prompt,
    parse_model_json,
)
from agent.app.state import AgentState, Intent
from backend.app.models.domain import ActionType, Priority
from backend.app.utils.ids import new_id

logger = logging.getLogger(__name__)


class IntentClassification(BaseModel):
    intent: str
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = []
    clarification: str | None = None


class EntityDraft(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_name: str | None = None
    assignee_is_me: bool = False
    due_date_phrase: str | None = None
    priority: str | None = None
    status: str | None = None
    reminder_phrase: str | None = None


@dataclass
class AgentContext:
    """Injected by the backend — READ-ONLY lookups. The graph has zero write access."""

    employee_id: str                          # caller's resolved EMP id
    employees: list[Any]                      # Employee snapshot for name resolution
    clock: Any                                # Clock (backend.app.utils.ids.Clock)
    task_lookup: Callable[..., list[dict[str, Any]]]   # keyword: assignee_id/title_contains
    source: str = "CHAT"                      # RecordSource of the input


TaskDict = dict[str, Any]


@dataclass
class AgentGraph:
    """Runs the node chain. Uses langgraph-compatible progress tracking; a simple synchronous
    pipeline is deliberate here because every path is linear (docs/agent-workflow.md §1)."""

    provider: ModelProvider | None = None

    def run(self, state: AgentState, ctx: AgentContext) -> AgentState:
        state = _normalize(state)
        state = _classify(state, self.provider)
        if state["intent"] == Intent.MEETING_EXTRACT:
            return _meeting_in_chat(state)
        state = _extract(state, self.provider)
        state = _resolve_employees(state, ctx)
        state = _resolve_dates(state, ctx)
        state = _validate_and_propose(state, ctx)
        return _compose_reply(state)


def _normalize(state: AgentState) -> AgentState:
    raw = state.get("raw_input", "")
    return {
        **state,
        "raw_input": raw,
        "normalized_input": " ".join(raw.strip().split()),
        "language": "en",
        "validation_issues": [],
        "proposed_actions": [],
        "requires_confirmation": False,
    }


def _classify(state: AgentState, provider: ModelProvider | None) -> AgentState:
    norm = state["normalized_input"]
    if provider is not None:
        try:
            raw = provider.complete_json(INTENT_SYSTEM_PROMPT, intent_user_prompt(norm))
            parsed_raw = parse_model_json(raw)
            if parsed_raw is None:
                raise ValueError("model output was not parseable JSON")  # → heuristic fallback
            parsed = IntentClassification.model_validate(parsed_raw)
            intent = Intent(parsed.intent.upper().strip())
            return {
                **state,
                "intent": intent.value,
                "intent_confidence": parsed.confidence,
                "intent_source": "model",
            }
        except ProviderUnavailableError:
            pass  # fall through to heuristics (workflow doc §5)
        except (ValidationError, ValueError):
            pass  # model failure: fall through to heuristics
    fb = heuristics.classify_intent_rule_based(norm)
    return {
        **state,
        "intent": str(fb["intent"]),
        "intent_confidence": fb["confidence"],
        "intent_source": "heuristic",
    }


def _extract(state: AgentState, provider: ModelProvider | None) -> AgentState:
    intent = Intent(state["intent"])
    norm = state["normalized_input"]
    draft: dict[str, Any] | None = None
    if provider is not None:
        try:
            raw = provider.complete_json(EXTRACT_SYSTEM_PROMPT, extraction_user_prompt(norm, intent.value))
            draft = parse_model_json(raw)
        except (ProviderUnavailableError, RuntimeError):
            draft = None
    if draft is None:  # no provider / unparseable → deterministic heuristic draft
        draft = heuristics.extract_heuristic(norm, intent.value)
    try:
        entities = EntityDraft.model_validate(draft)
    except ValidationError:
        entities = EntityDraft.model_validate(heuristics.extract_heuristic(norm, intent.value))
    return {**state, "intent": intent.value, "entities": entities.model_dump()}


def _resolve_employees(state: AgentState, ctx: AgentContext) -> AgentState:
    entities = dict(state["entities"])
    issues: list[str] = list(state.get("validation_issues", []))
    resolved: str | None = None
    if entities.get("assignee_is_me"):
        resolved = ctx.employee_id
    elif entities.get("assignee_name"):
        wanted = entities["assignee_name"].lower().strip()
        matches = [e for e in ctx.employees if e.name.lower().strip() == wanted]
        if len(matches) == 1:
            resolved = matches[0].employee_id
        elif len(matches) > 1:
            issues.append(
                "There are several employees named '" + entities["assignee_name"] + "': "
                + ", ".join(sorted(e.employee_id + " – " + e.name for e in matches))
                + ". Who do you mean?"
            )
        else:
            issues.append(
                "I couldn't find an employee named '" + entities["assignee_name"]
                + "'. People I know: " + ", ".join(e.employee_id + " – " + e.name for e in ctx.employees)
                + ". (employees are maintained in the sheet's Employees tab)"
            )
    entities["resolved_assignee_id"] = resolved
    return {**state, "entities": entities, "validation_issues": issues}


def _resolve_dates(state: AgentState, ctx: AgentContext) -> AgentState:
    entities = dict(state["entities"])
    issues: list[str] = list(state.get("validation_issues", []))
    today: date = ctx.clock.utcnow().date()

    due = resolution.resolve_due_date(entities.get("due_date_phrase"), today)
    entities["resolved_due_date"] = due.due_date
    if due.needs_clarification:
        issues.append(
            "I couldn't interpret the due date '" + str(entities.get("due_date_phrase"))
            + "'. Which day did you mean?"
        )

    reminder_phrase = entities.get("reminder_phrase")
    entities["resolved_reminder_at"] = None
    if reminder_phrase:
        base: date | None = None
        if due.due_date:
            y, m, dd = (int(v) for v in due.due_date.split("-"))
            base = date(y, m, dd)
        rr = resolution.parse_reminder_phrase(
            reminder_phrase, base_due_date=base, now=ctx.clock.utcnow(),
        )
        if rr.anchor is not None:
            entities["resolved_reminder_at"] = (
                rr.anchor.replace(tzinfo=timezone.utc).isoformat()
            )
        elif rr.needs_clarification:
            issues.append(
                "I couldn't resolve the reminder timing. Use something like "
                "'remind me one hour before the deadline' (task must be known) or an exact time."
            )
    return {**state, "entities": entities, "validation_issues": issues}


def _lookup(ctx: AgentContext, *, title_contains: str | None = None,
            assignee_id: str | None = None) -> list[TaskDict]:
    return ctx.task_lookup(title_contains=title_contains, assignee_id=assignee_id)


def _validate_and_propose(state: AgentState, ctx: AgentContext) -> AgentState:
    intent = Intent(state["intent"])
    entities = dict(state["entities"])
    issues: list[str] = list(state.get("validation_issues", []))
    proposed: list[TaskDict] = []

    def fail(msg: str) -> None:
        issues.append(msg)

    if intent is Intent.UNKNOWN:
        fail("I'm not sure what you'd like to do. Could you rephrase that?")

    elif intent in (Intent.CREATE_TASK, Intent.ASSIGN_TASK):
        title = (entities.get("title") or "").strip()
        assignee = entities.get("resolved_assignee_id")
        if not title:
            fail("What should the task be called?")
        if not assignee and not issues:
            if entities.get("assignee_name") is None:
                assignee = ctx.employee_id
                entities["assignee_name"] = None
                entities["assignee_is_me"] = True
                entities["resolved_assignee_id"] = assignee
            else:
                fail("Which employee should this be assigned to?")
        if not issues and title and assignee:
            dup = _find_open_duplicate(_lookup(ctx, assignee_id=assignee), title)
            if dup is not None:
                fail(
                    "A similar open task already exists for that person: '" + dup["title"]
                    + "' (" + dup["task_id"] + "). Should I update it instead?"
                )
            else:
                description = entities.get("description")
                keyword = intent.value
                proposed.append(
                    {
                        "action_id": new_id("ACT"),
                        "action_type": ActionType.ASSIGN_TASK.value
                        if keyword == "ASSIGN_TASK"
                        else ActionType.CREATE_TASK.value,
                        "payload": {
                            "title": title,
                            "description": description,
                            "assignee_id": assignee,
                            "due_date": entities.get("resolved_due_date"),
                            "priority": (entities.get("priority") or "MEDIUM").upper(),
                        },
                    }
                )

    elif intent in (Intent.UPDATE_TASK, Intent.COMPLETE_TASK, Intent.DELETE_TASK):
        title = entities.get("title")
        matches = _lookup(ctx, title_contains=title) if title else []
        if len(matches) == 0:
            fail("I couldn't find a task" + (" matching '" + title + "'." if title else "."))
        elif len(matches) > 1:
            fail(
                "I found several tasks. Which one — "
                + ", ".join(t["task_id"] + " '" + t["title"] + "'" for t in matches[:5])
                + "?"
            )
        else:
            task = matches[0]
            if intent is Intent.COMPLETE_TASK:
                proposed.append(
                    {"action_id": new_id("ACT"), "action_type": ActionType.COMPLETE_TASK.value,
                     "payload": {"task_id": task["task_id"], "comment": entities.get("description")}}
                )
            elif intent is Intent.DELETE_TASK:
                proposed.append(
                    {"action_id": new_id("ACT"), "action_type": ActionType.DELETE_TASK.value,
                     "payload": {"task_id": task["task_id"]}}
                )
            else:
                patch: TaskDict = {"task_id": task["task_id"]}
                if entities.get("resolved_assignee_id"):
                    patch["assignee_id"] = entities["resolved_assignee_id"]
                if entities.get("resolved_due_date"):
                    patch["due_date"] = entities["resolved_due_date"]
                if entities.get("priority"):
                    patch["priority"] = entities["priority"].upper()
                if entities.get("status"):
                    patch["status"] = entities["status"].upper()
                if entities.get("title") and entities.get("title") != task.get("title"):
                    patch["title"] = entities["title"]
                if len(patch) < 2:
                    fail("What should I change about task " + task["task_id"] + "?")
                else:
                    proposed.append(
                        {"action_id": new_id("ACT"), "action_type": ActionType.UPDATE_TASK.value,
                         "payload": patch}
                    )

    elif intent is Intent.CREATE_REMINDER:
        reminder_at = entities.get("resolved_reminder_at")
        title = entities.get("title")
        matches = _lookup(ctx, title_contains=title) if title else []
        if not reminder_at and len(matches) == 1 and matches[0].get("due_date"):
            # relative phrase ("two hours before the deadline") anchored on the known due date
            base = _parse_date(matches[0]["due_date"])
            if base is not None:
                rr = resolution.parse_reminder_phrase(
                    entities.get("reminder_phrase") or "",
                    base_due_date=base, now=ctx.clock.utcnow(),
                )
                if rr.anchor is not None:
                    reminder_at = rr.anchor.replace(tzinfo=timezone.utc).isoformat()
        if not reminder_at:
            if not any("reminder" in i.lower() or "remind" in i.lower() for i in issues):
                fail(
                    "I need a task and a time for the reminder. Try 'remind me one hour before "
                    "the deadline for <task>' or give an exact time."
                )
        elif len(matches) == 1:
            proposed.append(
                {"action_id": new_id("ACT"), "action_type": ActionType.CREATE_REMINDER.value,
                 "payload": {"task_id": matches[0]["task_id"], "employee_id": ctx.employee_id,
                             "scheduled_at": reminder_at}}
            )
        elif len(matches) == 0:
            fail("I couldn't find a task to attach the reminder to.")
        else:
            fail(
                "Several tasks match. Which one? "
                + ", ".join(t["task_id"] + " '" + t["title"] + "'" for t in matches[:5])
            )

    return {
        **state,
        "proposed_actions": proposed,
        "validation_issues": issues,
        "requires_confirmation": bool(proposed),
        "entities": entities,
    }


def resolution_err(issues: list[str], reminder_at: str | None) -> bool:
    del issues  # resolved-time failures already appended in _resolve_dates
    return not reminder_at


def _parse_date(date_iso: str):
    try:
        y, m, d = (int(v) for v in date_iso.split("-"))
        return date(y, m, d)
    except (ValueError, AttributeError, TypeError):
        return None


def _compose_reply(state: AgentState) -> AgentState:
    issues = list(state.get("validation_issues", []))
    proposed = list(state.get("proposed_actions", []))
    intent = Intent(state["intent"])

    if issues and not proposed:
        return {**state, "system_reply": issues[0], "requires_confirmation": False}

    if proposed:
        p = proposed[0]
        action_type = p["action_type"]
        payload = p["payload"]
        if action_type == ActionType.CREATE_REMINDER.value:
            msg = (
                "Reminder scheduled — I'd attach it to task " + payload["task_id"]
                + " at " + payload["scheduled_at"] + ". Confirm?"
            )
        elif action_type in (ActionType.CREATE_TASK.value, ActionType.ASSIGN_TASK.value):
            title = payload.get("title")
            assignee = payload.get("assignee_id")
            due = payload.get("due_date")
            msg = "I found a task:\n"
            msg += "- " + title + "\n"
            if assignee:
                msg += f"- Assigned to: {assignee}\n"
            if due:
                msg += f"- Due date: {due}\n"
            msg += "\nShould I create this task?"
        elif action_type == ActionType.COMPLETE_TASK.value:
            msg = "Should I mark task " + payload["task_id"] + " as DONE?"
        elif action_type == ActionType.DELETE_TASK.value:
            msg = "Should I delete task " + payload["task_id"] + "? This cannot be undone."
        else:
            msg = "Here is the change I propose: " + ", ".join(
                k + "=" + str(payload[k]) for k in payload if k != "task_id"
            ) + " on task " + payload["task_id"] + ". Confirm?"
        return {**state, "system_reply": msg, "requires_confirmation": True}

    read_only = {
        Intent.QUERY_TASKS: "Here is what I found for your pending tasks.",
        Intent.QUERY_ACTIVITY: "Here is a summary of recent activity.",
    }.get(intent, "")
    if read_only:
        return {**state, "system_reply": read_only, "requires_confirmation": False}

    return {
        **state,
        "system_reply": "Could you give me a little more detail about the task?",
        "requires_confirmation": False,
    }


def _meeting_in_chat(state: AgentState) -> AgentState:
    return {
        **state,
        "system_reply": (
            "For meeting notes, use the Meeting extraction feature (paste the notes there). "
            "In chat I can help you create, complete, assign and query tasks or set reminders."
        ),
        "proposed_actions": [],
        "validation_issues": [],
        "requires_confirmation": False,
    }


def _find_open_duplicate(tasks: list[TaskDict], title: str) -> TaskDict | None:
    needle = title.lower().strip()
    for t in tasks:
        if (t.get("status") in ("TODO", "IN_PROGRESS", "BLOCKED")) and (
            (t.get("title") or "").lower().strip() == needle
        ):
            return t
    return None
