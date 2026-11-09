"""Deterministic date/reminder resolution (agent/AGENTS.md, docs/agent-workflow.md §3).

Converts date phrases into ISO `YYYY-MM-DD` anchored on the injected "today"; converts relative
reminder phrasing into absolute UTC offsets. Ambiguous phrases produce clarify signals — never
guessed dates (zero-trust rule, root AGENTS.md §4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


@dataclass(frozen=True)
class ResolvedDueDate:
    due_date: str | None
    needs_clarification: bool


@dataclass(frozen=True)
class ResolvedReminder:
    anchor: datetime | None  # absolute target time
    offset: timedelta | None  # offset relative to base (used when base provided later)
    needs_clarification: bool


def next_weekday(weekday: int, d: date) -> date:
    days_ahead = (weekday - d.weekday()) % 7
    return d + timedelta(days=days_ahead)


def resolve_due_date(phrase: str | None, today: date) -> ResolvedDueDate:
    if not phrase:
        return ResolvedDueDate(due_date=None, needs_clarification=False)
    p = " ".join(phrase.strip().lower().split())
    is_next = p.startswith("next ") or " next " in p
    p = re.sub(r"^(this|on|by|next)\s+", "", p)

    if p in ("today",):
        return ResolvedDueDate(today.isoformat(), False)
    if p in ("tomorrow",):
        return ResolvedDueDate((today + timedelta(days=1)).isoformat(), False)
    weekday = WEEKDAYS.get(p)
    if weekday is not None:
        d = next_weekday(weekday, today)
        if is_next and d <= today:
            # "next Monday" said on a Monday → a week ahead (never same day)
            d = d + timedelta(days=7)
        return ResolvedDueDate(d.isoformat(), False)

    m = re.fullmatch(r"(\d+)\s*days?\s*from\s*(now|today)", p)
    if m:
        return ResolvedDueDate((today + timedelta(days=int(m.group(1)))).isoformat(), False)

    m = re.fullmatch(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?", p)
    if m and m.group(1) in MONTHS and m.group(2).isdigit():
        month, day = MONTHS[m.group(1)], int(m.group(2))
        year = today.year + (1 if (month, day) < (today.month, today.day) else 0)
        try:
            return ResolvedDueDate(date(year, month, day).isoformat(), False)
        except ValueError:
            return ResolvedDueDate(None, True)

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", p)
    if m:
        try:
            return ResolvedDueDate(date(*map(int, m.groups())).isoformat(), False)
        except ValueError:
            return ResolvedDueDate(None, True)

    return ResolvedDueDate(None, True)


DEFINITE_RETURN_HOURS = 17  # 09:00 local-per-day convention of the data model


def parse_reminder_phrase(phrase: str, *, base_due_date: date | None, now: datetime) -> ResolvedReminder:
    """'two hours before the deadline' → absolute UTC target (needs base due date)."""
    p = " ".join(phrase.strip().lower().split())
    if not p:
        return ResolvedReminder(None, None, True)
    p = _normalize_number_words(p)

    m = re.fullmatch(
        r"(\d+)\s*(minutes?|hours?|hrs|days?)\s*(?:before|prior to)\s+(?:the\s+)?(?:task\s+)?deadline",
        p,
    )
    if m:
        qty = int(m.group(1))
        unit = m.group(2)
        delta = _unit_delta(unit, qty)
        if base_due_date is None:
            return ResolvedReminder(None, delta, False)
        base = datetime(base_due_date.year, base_due_date.month, base_due_date.day, 9, 0)
        return ResolvedReminder(anchor=base - delta, offset=None, needs_clarification=False)

    m = re.fullmatch(r"(\d+)\s*(minutes?|hours?|hrs|days?)\s*from\s*now", p)
    if m:
        delta = _unit_delta(m.group(2), int(m.group(1)))
        return ResolvedReminder(anchor=now + delta, offset=None, needs_clarification=False)

    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})[t ](\d{2}):(\d{2})(?::(\d{2}))?", p)
    if m:
        try:
            anchor = datetime(
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), int(m.group(5)),
            )
        except (ValueError, TypeError):
            return ResolvedReminder(None, None, True)
        return ResolvedReminder(anchor=anchor, offset=None, needs_clarification=False)

    # "tomorrow at 11am"
    m = re.fullmatch(r"(tomorrow|today) at (\d{1,2})\s*(am|pm)", p)
    if m:
        day_offset = 1 if m.group(1) == "tomorrow" else 0
        hour = int(m.group(2)) % 12 + (12 if m.group(3) == "pm" else 0)
        d = now.date() + timedelta(days=day_offset)
        return ResolvedReminder(anchor=datetime(d.year, d.month, d.day, hour), offset=None, needs_clarification=False)

    return ResolvedReminder(None, None, True)


def _normalize_number_words(p: str) -> str:
    """'two hours before' → '2 hours before' (deterministic word→digit for time phrases)."""
    from agent.app.nodes.heuristics import NUMBER_WORDS

    first, _, rest = p.partition(" ")
    if first.isdigit():
        return p
    if first in NUMBER_WORDS:
        return f"{NUMBER_WORDS[first]} {rest}"
    return p


def _unit_delta(unit: str, qty: int) -> timedelta:
    if unit.startswith("day"):
        return timedelta(days=qty)
    if unit.startswith("hour") or unit == "hrs":
        return timedelta(hours=qty)
    return timedelta(minutes=qty)
