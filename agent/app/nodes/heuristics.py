"""Deterministic fallbacks (docs/agent-workflow.md §5 — graceful clarification, not fabrication).

Used ONLY when the model provider is unavailable or returns unparseable JSON. These functions
produce the *same draft structures* as the LLM prompts so downstream nodes are provider-agnostic.
They are keyword/regex heuristics — never trusted further than model output (validations below).
"""

from __future__ import annotations

import re
from typing import Any

from agent.app.state import Intent

_NEGATIONS = (r"\bnot\b",)

NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "thirty": 30, "sixty": 60,
}


def classify_intent_rule_based(normalized: str) -> dict[str, Any]:
    """Keyword/regex decision table mirroring prompts/templates.py INTENT_SYSTEM_PROMPT."""
    text = " ".join(normalized.strip().lower().split())
    if re.search(r"\b(what are|list|show)\b.*\btasks?|pending tasks|my tasks\b", text):
        return {"intent": Intent.QUERY_TASKS, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\bsummari[sz]e\b|\bwhat (did|has) everyone\b|\bworked on\b", text):
        return {"intent": Intent.QUERY_ACTIVITY, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"^assign\b|=>\bassign\b", text) or re.search(r"\bassign\b .+ \bto\b", text):
        return {"intent": Intent.ASSIGN_TASK, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(remind|reminder)\b", text):
        return {"intent": Intent.CREATE_REMINDER, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(schedul\w*|set up|arrange)\b.*\bmeeting\b|\bmeeting notes?\b|\btranscript\b", text):
        return {"intent": Intent.MEETING_EXTRACT, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(delete|remove)\b.*\btask\b", text):
        return {"intent": Intent.DELETE_TASK, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(completed|completed|done with|finished|complete the)\b", text) or re.search(
        r"\bmark\b .*\b(done|completed)\b", text,
    ):
        return {"intent": Intent.COMPLETE_TASK, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(mark|set|change|reschedul\w*|update|move)\b", text):
        return {"intent": Intent.UPDATE_TASK, "confidence": 0.6, "missing_fields": [], "clarification": None}
    if re.search(r"\b(i need to|i have to|create|add|new task)\b", text) or re.search(
        r"\bi will\b", text,
    ):
        return {"intent": Intent.CREATE_TASK, "confidence": 0.6, "missing_fields": [], "clarification": None}
    return {"intent": Intent.UNKNOWN, "confidence": 0.1, "missing_fields": [], "clarification": None}


def extract_heuristic(normalized: str, intent: str) -> dict[str, Any]:
    """Best-effort draft extraction; downstream validation confirms/asks."""
    text = normalized.lower()
    out: dict[str, Any] = {
        "title": None,
        "description": None,
        "assignee_name": None,
        "assignee_is_me": False,
        "due_date_phrase": None,
        "priority": None,
        "status": None,
        "reminder_phrase": None,
    }
    m = re.search(
        r"\b(assign)\b\s*(?P<title>.+?)\s+\bto\b\s+(?P<who>me|\w+)",
        text,
    )
    if m:
        out["assignee_is_me"] = m.group("who") == "me"
        who = m.group("who")
        out["assignee_name"] = who.capitalize() if who != "me" else None
        out["title"] = m.group("title").strip()
    else:
        m = re.match(
            r"^(?:i need to|i have to|i will)\s+(?P<title>.+?)(?:\s+by\s+(?P<when>.+))?$",
            text,
        )
        if m:
            out["title"] = m.group("title").strip()
            out["assignee_is_me"] = True
            out["due_date_phrase"] = m.group("when")
        else:
            m = re.search(
                r"\b(?:completed|done with|finished|complete the|completed the)\b\s*(?P<rest>.+)$",
                text,
            )
            if m:
                out["title"] = m.group("rest").strip() or text.strip()

            else:
                m = re.search(r"\bremind me\b(?P<rest>.*)$", text)
                if m:
                    rest = m.group("rest").strip()
                    # split "about <task title> <timing phrase>" at the time-related words.
                    tm = re.search(
                        r"(?P<pre>.+?)\s+((?:\d+|one|two|three|four|five|six|seven|eight|nine|"
                        r"ten|fifteen|thirty|sixty|an)\s+"
                        r"(?:minutes?|hours?|hrs|days?)\b)",
                        rest,
                    )
                    if tm and re.search(r"(?:before|prior to|from now)", rest):
                        title_text = tm.group("pre").strip()
                        title_text = re.sub(r"^about\s+", "", title_text)
                        out["title"] = title_text or None
                        out["reminder_phrase"] = rest[tm.start(2):][:200]
                    else:
                        out["reminder_phrase"] = rest[:200] or None
                        out["title"] = None
    if not out["title"] and not out["reminder_phrase"]:
        # last resort: full text (words trimmed) so classification never fabricates none-fields
        out["title"] = normalized.strip()[:140]
    m = re.search(r"\b(high|med(?:ium)?|low) priority\b", text)
    if m:
        p = m.group(1).upper()
        out["priority"] = "HIGH" if p == "HIGH" else ("LOW" if p == "LOW" else "MEDIUM")
    return out
