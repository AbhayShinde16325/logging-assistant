"""MockModelProvider fixtures — prompt ↔ structured-output synchronization
(docs/testing-strategy.md "regenerate fixtures when prompts change")."""

from __future__ import annotations

import json

import pytest

from agent.app.graph import AgentContext, AgentGraph
from agent.app.models.providers import MockModelProvider
from agent.app.prompts.templates import (
    MOCK_FIXTURE_CREATE_TASK,
    MOCK_FIXTURE_QUERY_TASKS,
    MOCK_FIXTURE_UNKNOWN,
)
from backend.app.utils.ids import to_iso
from tests.unit.conftest import SEED_TIME
import datetime as dt


def _ctx(fake_clock) -> AgentContext:
    def lookup(**kw) -> list[dict]:
        return []

    return AgentContext(
        employee_id="EMP-001",
        employees=[],
        clock=fake_clock,
        task_lookup=lookup,
    )


@pytest.fixture()
def fake_provider() -> MockModelProvider:
    return MockModelProvider(canned={
        "CLASSIFY_INTENT": MOCK_FIXTURE_CREATE_TASK,
        "EXTRACT_TASK": json.dumps({
            "title": "Competitor research",
            "description": "Research competitor products",
            "assignee_name": None,
            "assignee_is_me": True,
            "due_date_phrase": "Wednesday",
            "priority": "MEDIUM",
            "status": "TODO",
            "reminder_phrase": None,
        }),
    })


def test_model_path_valid_json_produces_valid_schema提案(fake_provider, fake_clock) -> None:
    graph = AgentGraph(provider=fake_provider)
    state = graph.run({"raw_input": "I need to finish competitor research by Wednesday"},
                      _ctx(fake_clock))
    proposals = state["proposed_actions"]
    assert proposals and proposals[0]["action_type"] == "CREATE_TASK"
    assert proposals[0]["payload"]["title"] == "Competitor research"


def test_invalid_model_json_persists_fallback(fake_provider, fake_clock) -> None:
    bad_provider = MockModelProvider(canned={
        "CLASSIFY_INTENT": "not-json",   # invalid → provider retry path → heuristic fallback
        "EXTRACT_TASK": "not-json",
    })
    graph = AgentGraph(provider=bad_provider)
    state = graph.run({"raw_input": "i need to fix login bug by tomorrow"}, _ctx(fake_clock))
    # the graph must degrade deterministically, never crash or fabricate an ID
    assert state["intent_source"] == "heuristic"
    assert (state.get("proposed_actions") or state.get("validation_issues"))


def test_known_fixture_completes_query(fake_provider, fake_clock) -> None:
    provider = MockModelProvider(canned={"CLASSIFY_INTENT": MOCK_FIXTURE_QUERY_TASKS})
    graph = AgentGraph(provider=provider)
    state = graph.run({"raw_input": "what are my pending tasks"}, _ctx(fake_clock))
    assert state["intent"] == "QUERY_TASKS"
    assert state["proposed_actions"] == []


def test_unknown_fixture_reply(fake_provider, fake_clock) -> None:
    provider = MockModelProvider(canned={"CLASSIFY_INTENT": MOCK_FIXTURE_UNKNOWN})
    graph = AgentGraph(provider=provider)
    state = graph.run({"raw_input": "sunset photos pls"}, _ctx(fake_clock))
    assert state["requires_confirmation"] is False
    assert state.get("system_reply")
