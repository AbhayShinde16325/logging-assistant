"""Heuristic intent classification + extraction (docs/testing-strategy.md — task extraction)."""

from __future__ import annotations

import pytest

from agent.app.nodes import heuristics


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("i need to research competitor products by wednesday", "CREATE_TASK"),
        ("assign competitor research to priya", "ASSIGN_TASK"),
        ("i completed the login module", "COMPLETE_TASK"),
        ("what are my pending tasks", "QUERY_TASKS"),
        ("summarize what everyone worked on this week", "QUERY_ACTIVITY"),
        ("remind me about the report two hours before the deadline", "CREATE_REMINDER"),
        ("schedule a team meeting tomorrow at 11 am", "MEETING_EXTRACT"),
        ("delete task TASK-deadbeef", "DELETE_TASK"),
        ("mark T1 blocked please", "UPDATE_TASK"),
        ("totally unrelated chit chat", "UNKNOWN"),
    ],
)
def test_intent_rule_based(text, expected) -> None:
    intent = heuristics.classify_intent_rule_based(text)
    assert str(intent["intent"]) == expected


def test_extraction_create_task_me() -> None:
    draft = heuristics.extract_heuristic(
        "i need to research competitor products by wednesday", "CREATE_TASK",
    )
    assert draft["assignee_is_me"] is True
    assert "research competitor products" in draft["title"]
    assert draft["due_date_phrase"] == "wednesday"


def test_extraction_assign_to_named_person() -> None:
    draft = heuristics.extract_heuristic("assign competitor research to priya", "ASSIGN_TASK")
    assert draft["assignee_name"] == "Priya"
    assert draft["assignee_is_me"] is False
    assert draft["title"] == "competitor research"


def test_extraction_completion_titles_task_fragment() -> None:
    draft = heuristics.extract_heuristic("i completed the authentication module", "COMPLETE_TASK")
    assert draft["title"] == "the authentication module"


def test_extraction_priority_detection() -> None:
    draft = heuristics.extract_heuristic("i need to fix the bug high priority by today", "CREATE_TASK")
    assert draft["priority"] == "HIGH"
