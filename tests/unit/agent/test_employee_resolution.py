"""Agent graph end-to-end with deterministic (heuristic) path — employee resolution, proposals,
duplicate handling and clarification branches (tasks T-050/T-051, docs/testing-strategy.md
"employee identification"). Model-path fixture validation lives in test_extraction_fixtures.py."""

from __future__ import annotations

import pytest

from agent.app.graph import AgentContext, AgentGraph
from agent.app.state import AgentState
from backend.app.utils.ids import to_iso
from tests.unit.conftest import FakeClock

SEED = __import__("datetime").datetime(2026, 11, 9, 9, 0, 0)


@pytest.fixture()
def ctx(monkeypatch, fake_clock):
    tasks_store: list[dict] = []

    def lookup(*, title_contains=None, assignee_id=None) -> list[dict]:
        out: list[dict] = []
        if title_contains is None:
            candidates = tasks_store
        else:
            needle = " ".join(title_contains.lower().split())
            variants = {needle, needle.removeprefix("the "), needle.removeprefix("a ")}
            candidates = [
                t for t in tasks_store
                if any(v in " ".join(t["title"].lower().split()) for v in variants)
            ]
        for t in candidates:
            if assignee_id is not None and t["assignee_id"] != assignee_id:
                continue
            out.append(t)
        return out

    employees = [E for E in (
        ("EMP-001", "Abhay", "a@example.com", "Engineer"),
        ("EMP-002", "Priya", "p@example.com", "Engineer"),
    ) for E in [E]] if False else [
        _e(eid, name) for eid, name in (("EMP-001", "Abhay"), ("EMP-002", "Priya"))
    ]
    return AgentContext(
        employee_id="EMP-001",
        employees=list(employees),
        clock=fake_clock,
        task_lookup=lookup,
    )


def _e(employee_id: str, name: str):
    from backend.app.models.domain import Employee

    return Employee(
        employee_id=employee_id, name=name, email=f"{name.lower()}@x.io",
        role="Member", created_at=to_iso(SEED),
    )


@pytest.fixture()
def graph():
    return AgentGraph(provider=None)  # deterministic heuristic path


def run(graph: AgentGraph, ctx: AgentContext, text: str) -> AgentState:
    return graph.run({"raw_input": text}, ctx)


def _one_proposal(state) -> tuple[str, dict]:
    proposals = state.get("proposed_actions", [])
    assert len(proposals) >= 1, state.get("validation_issues")
    assert len(proposals) == 1, proposals
    p = proposals[0]
    assert p["action_id"].startswith("ACT-") and len(p["action_id"]) == 12
    return p["action_type"], p


def test_create_task_assigned_to_me(graph, ctx) -> None:
    state = run(graph, ctx, "I need to research competitor products by Wednesday")
    kind, p = _one_proposal(state)
    assert kind == "CREATE_TASK"
    assert p["payload"]["assignee_id"] == "EMP-001"
    assert p["payload"]["due_date"] == "2026-11-11"
    assert "Competitor" in p["payload"]["title"].title() or "research" in p["payload"]["title"].lower()
    assert state["requires_confirmation"] is True
    assert "confirm" in state["system_reply"].lower() or "should i" in state["system_reply"].lower()


def test_assign_to_named_employee_resolves(graph, ctx) -> None:
    state = run(graph, ctx, "assign competitor research to Priya")
    kind, p = _one_proposal(state)
    assert kind in ("CREATE_TASK", "ASSIGN_TASK")
    assert p["payload"]["assignee_id"] == "EMP-002"


def test_unknown_employee_asks_clarification(graph, ctx) -> None:
    state = run(graph, ctx, "assign competitor research to Sanjay")
    assert not state.get("proposed_actions")
    assert any("couldn't find an employee" in i.lower() or "who do you mean" in i.lower()
               for i in state.get("validation_issues", []))


def test_ambiguous_duplicate_blocks_creation(graph, ctx) -> None:
    ctx.task_lookup = lambda **kw: [
        {"task_id": "TASK-1", "title": "Research competitor products", "assignee_id": "EMP-001",
         "status": "TODO"}
    ]
    state = run(graph, ctx, "I need to research competitor products")
    assert not state.get("proposed_actions")
    assert any("already exists" in i for i in state.get("validation_issues", []))


def test_complete_task_proposal_targets_existing(graph, ctx) -> None:
    ctx.task_lookup = lambda **kw: [
        {"task_id": "TASK-2", "title": "authentication module", "assignee_id": "EMP-001",
         "status": "IN_PROGRESS"}
    ]
    state = run(graph, ctx, "I completed the authentication module")
    kind, p = _one_proposal(state)
    assert kind == "COMPLETE_TASK"
    assert p["payload"]["task_id"] == "TASK-2"


def test_reminder_for_existing_task(graph, ctx) -> None:
    ctx.task_lookup = lambda **kw: [
        {"task_id": "TASK-3", "title": "quarterly report", "assignee_id": "EMP-001",
         "status": "TODO", "due_date": "2026-11-11"}
    ]
    state = run(graph, ctx, "remind me about the quarterly report two hours before the deadline")
    kind, p = _one_proposal(state)
    assert kind == "CREATE_REMINDER"
    assert p["payload"]["task_id"] == "TASK-3"
    # deadline convention = 09:00 on the due date → 2h before = 07:00 on that day
    assert p["payload"]["scheduled_at"].startswith("2026-11-11T07:00")


def test_unknown_intent_asks_clarification(graph, ctx) -> None:
    state = run(graph, ctx, "hello there!")
    assert not state.get("proposed_actions")
    assert not state.get("requires_confirmation")


def test_query_tasks_is_read_only(graph, ctx) -> None:
    state = run(graph, ctx, "what are my pending tasks")
    assert state["intent"] == "QUERY_TASKS"
    assert not state.get("proposed_actions")
    assert state["requires_confirmation"] is False
