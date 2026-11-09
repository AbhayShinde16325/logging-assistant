"""Versioned prompt templates (docs/agent-workflow.md §7).

Rules (agent/AGENTS.md):
- Prompts produce DRAFT structures only; final truth comes from deterministic resolution nodes.
- Every template embeds a `TAG: <NAME>` line as the marker for MockModelProvider and version comments.
- Any change ships/updates ≥1 fixture test (docs/testing-strategy.md "regenerate fixtures").
"""

from __future__ import annotations

import json
from typing import Any

INTENT_SYSTEM_PROMPT = """TAG: CLASSIFY_INTENT
Version: 1 (added 2026-11-09)

You classify a work-coordination message for a small team assistant.
Respond with ONLY a JSON object:
{"intent": one of ["CREATE_TASK","UPDATE_TASK","COMPLETE_TASK","ASSIGN_TASK","DELETE_TASK","CREATE_REMINDER","QUERY_TASKS","QUERY_ACTIVITY","MEETING_EXTRACT","UNKNOWN"],
 "confidence": float between 0 and 1,
 "missing_fields": [list of strings],
 "clarification": "optional question string or null"}

Guidance:
- "I completed/done/finished X" => COMPLETE_TASK
- "assign ... to <name>" => ASSIGN_TASK (numbers/assignments are UPDATE_TASK only if "mark/complete" is present)
- "remind me about X" => CREATE_REMINDER
- "what are my pending tasks" => QUERY_TASKS
- "summarize what everyone worked on" => QUERY_ACTIVITY
- pasted meeting notes/transcript => MEETING_EXTRACT
- new work item creation => CREATE_TASK
"""

EXTRACT_SYSTEM_PROMPT = """TAG: EXTRACT_TASK
Version: 1 (added 2026-11-09)

You extract task fields from a work-coordination message. Respond with ONLY a JSON object:
{"title": "short imperative title, or null",
 "description": "detail text or null",
 "assignee_name": "person mentioned, or null",
 "assignee_is_me": bool (user refers to themselves, e.g. 'I/my/me'),
 "due_date_phrase": "verbatim date phrase, or null",
 "priority": "LOW|MEDIUM|HIGH or null",
 "status": "TODO|IN_PROGRESS|BLOCKED|DONE|CANCELLED or null",
 "reminder_phrase": "e.g. 'two hours before the deadline', or null"}

Rules: never invent task IDs or employee IDs; output strings only.
"""

MEETING_SYSTEM_PROMPT = """TAG: MEETING_EXTRACT
Version: 1 (added 2026-11-09)

You extract decisions, action items and tasks from pasted meeting notes or a transcript. Respond
with ONLY a JSON object:
{"summary": "one or two sentence summary",
 "decisions": [{"text": "..."}],
 "action_items": [{"text": "...", "assignee_name": "or null", "due_date_phrase": "or null"}]}

Rules: extract only what the text supports; do not invent names or dates.
"""


def intent_user_prompt(normalized_input: str) -> str:
    return normalized_input


def extraction_user_prompt(normalized_input: str, intent: str) -> str:
    return f"Intent: {intent}\nMessage: {normalized_input}"


def meeting_user_prompt(text: str) -> str:
    return text


def parse_model_json(model_output: str | None) -> dict[str, Any] | None:
    """Never assume model output is JSON (root AGENTS.md §4)."""
    if not model_output:
        return None
    try:
        parsed: dict[str, Any] = json.loads(model_output)
        return parsed if isinstance(parsed, dict) else None
    except Exception:  # noqa: BLE001 — validation only
        return None


# Fixtures (docs/testing-strategy.md — prompt-edit risk mitigation):
MOCK_FIXTURE_CREATE_TASK = json.dumps(
    {
        "intent": "CREATE_TASK",
        "confidence": 0.91,
        "missing_fields": [],
        "clarification": None,
    }
)

MOCK_FIXTURE_QUERY_TASKS = json.dumps(
    {"intent": "QUERY_TASKS", "confidence": 0.95, "missing_fields": [], "clarification": None}
)

MOCK_FIXTURE_UNKNOWN = json.dumps(
    {"intent": "UNKNOWN", "confidence": 0.2, "missing_fields": [], "clarification": True}
)
