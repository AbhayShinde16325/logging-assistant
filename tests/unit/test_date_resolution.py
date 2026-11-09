"""Tester for date/reminder resolution (docs/testing-strategy.md — date extraction)."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from agent.app.nodes import resolution

TODAY = date(2026, 11, 9)  # Monday
NOW = datetime(2026, 11, 9, 9, 0, 0, tzinfo=timezone.utc)


def test_ignores_empty() -> None:
    r = resolution.resolve_due_date(None, TODAY)
    assert r.due_date is None and not r.needs_clarification


def test_today_and_tomorrow() -> None:
    assert resolution.resolve_due_date("today", TODAY).due_date == "2026-11-09"
    assert resolution.resolve_due_date("tomorrow", TODAY).due_date == "2026-11-10"


def test_weekday_within_week() -> None:
    r = resolution.resolve_due_date("Wednesday", TODAY)
    assert r.due_date == "2026-11-11"  # Mon → Wed same week


def test_next_weekday_jumps_a_week() -> None:
    r = resolution.resolve_due_date("next Monday", TODAY)
    assert r.due_date == "2026-11-16"


def test_month_day_crosses_year_when_past() -> None:
    r = resolution.resolve_due_date("March 3", TODAY)
    assert r.due_date == "2027-03-03"


def test_absolute_iso_passes_through() -> None:
    r = resolution.resolve_due_date("2026-11-15", TODAY)
    assert r.due_date == "2026-11-15"


def test_ambiguous_gibberish_requests_clarification() -> None:
    r = resolution.resolve_due_date("someday soon", TODAY)
    assert r.due_date is None and r.needs_clarification


def test_by_prefix_is_stripped() -> None:
    r = resolution.resolve_due_date("by Friday", TODAY)
    assert r.due_date == "2026-11-13"


# ---- reminder phrases ---------------------------------------------------------
def test_reminder_hours_before_deadline() -> None:
    rr = resolution.parse_reminder_phrase(
        "two hours before the deadline", base_due_date=date(2026, 11, 11), now=NOW,
    )
    # deadline convention: 09:00 on the due date
    assert rr.anchor == datetime(2026, 11, 11, 7, 0)


def test_reminder_days_before_deadline() -> None:
    rr = resolution.parse_reminder_phrase(
        "1 day before the deadline", base_due_date=date(2026, 11, 11), now=NOW,
    )
    assert rr.anchor == datetime(2026, 11, 10, 9, 0)


def test_reminder_without_base_stays_unclear() -> None:
    rr = resolution.parse_reminder_phrase("two hours before", base_due_date=None, now=NOW)
    # base unknown → deferred resolution (no anchor). Clarify arrives upstream.
    assert rr.needs_clarification or rr.offset is not None


def test_reminder_from_now() -> None:
    rr = resolution.parse_reminder_phrase("30 minutes from now", base_due_date=None, now=NOW)
    assert rr.anchor == datetime(2026, 11, 9, 9, 30, tzinfo=timezone.utc)


def test_reminder_absolute_time() -> None:
    rr = resolution.parse_reminder_phrase(
        "2026-11-10 09:30", base_due_date=None, now=NOW,
    )
    assert (rr.anchor is not None and not rr.needs_clarification)


def test_reminder_garbage_needs_clarification() -> None:
    rr = resolution.parse_reminder_phrase("at some point", base_due_date=None, now=NOW)
    assert rr.needs_clarification
