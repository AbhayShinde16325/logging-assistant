"""AgentState + supporting enums (docs/agent-workflow.md §2 — authoritative)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict


class Intent(StrEnum):
    CREATE_TASK = "CREATE_TASK"
    UPDATE_TASK = "UPDATE_TASK"
    COMPLETE_TASK = "COMPLETE_TASK"
    ASSIGN_TASK = "ASSIGN_TASK"
    DELETE_TASK = "DELETE_TASK"
    CREATE_REMINDER = "CREATE_REMINDER"
    QUERY_TASKS = "QUERY_TASKS"
    QUERY_ACTIVITY = "QUERY_ACTIVITY"
    MEETING_EXTRACT = "MEETING_EXTRACT"
    UNKNOWN = "UNKNOWN"


class AgentState(TypedDict, total=False):
    raw_input: str
    normalized_input: str
    language: str
    employee_id: str            # caller (request-scoped, validated upstream)
    intent: str                 # Intent value
    intent_confidence: float
    intent_source: str          # "model" | "heuristic"
    entities: dict[str, Any]    # LLM/heuristic draft — never trusted, resolved downstream
    proposed_actions: list[dict[str, Any]]
    validation_issues: list[str]
    system_reply: str
    requires_confirmation: bool
    error: str | None
    source: str                 # RecordSource of the user input (CHAT/VOICE/MEETING)
    meeting_title: str | None
