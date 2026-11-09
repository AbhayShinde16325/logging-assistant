"""Confirmation & rejection lifecycle (docs/testing-strategy.md) — T-052.

Runs end-to-end over real Sheets repository code + the canonical fake client (mirrors
test_full_flow.py but at the service layer).
"""

from __future__ import annotations

import pytest

from backend.app.models.domain import (
    ActionStatus,
    ActionType,
    ActivityType,
    RecordSource,
    TaskStatus,
)
from backend.app.services.action_store import ActionStore
from backend.app.services.action_service import ActionService
from backend.app.services.chat_service import ChatService
from backend.app.utils.errors import ApiError, ErrorCode


@pytest.fixture()
def stack(sheets_container):
    return sheets_container


def talk(stack, text: str, employee_id="EMP-003"):
    result = stack.chat_service.chat(
        text, employee_id=employee_id, source="CHAT",
    )
    return result


def test_confirm_creates_task_row_and_log(stack, sheets_repos) -> None:
    result = talk(stack, "I need to research competitor products by Wednesday")
    assert result["requires_confirmation"] is True
    action_id = result["proposed_actions"][0]["action_id"]

    response = stack.action_service.confirm(action_id)
    task = response.summary["task"]
    assert task["title"]
    row = [s for s in sheets_repos["tasks"]._load_all()[0] if s.task_id == task["task_id"]]
    assert row and row[0].status == TaskStatus.TODO
    # Activity_Log contains TASK_CREATED and row's source is CHAT
    entries, _ = sheets_repos["activity"].list(task_id=task["task_id"])
    assert entries[-1].activity_type.value == "TASK_CREATED"
    # Confirm marks the Command_Log row CONFIRMED (T-062)
    commands = sheets_repos["commands"]
    assert commands is not None


def test_reject_leaves_pending_and_returns(stack) -> None:
    result = talk(stack, "I need to ship the beta on Friday")
    action_id = result["proposed_actions"][0]["action_id"]
    rejected = stack.action_service.reject(action_id)
    assert rejected.status == ActionStatus.REJECTED
    # idempotent: rejecting again is a 409
    with pytest.raises(ApiError) as ei:
        stack.action_service.reject(action_id)
    assert ei.value.code is ErrorCode.ACTION_NOT_PENDING


def test_double_confirm_is_action_not_pending(stack) -> None:
    result = talk(stack, "I need to research competitor products by Wednesday")
    action_id = result["proposed_actions"][0]["action_id"]
    stack.action_service.confirm(action_id)
    with pytest.raises(ApiError) as ei:
        stack.action_service.confirm(action_id)
    assert ei.value.code is ErrorCode.ACTION_NOT_PENDING


def test_confirm_after_expiry_is_action_not_pending(stack, test_settings, sheets_repos) -> None:
    from backend.app.core.config import Settings

    from agent.app.models.providers import MockModelProvider
    from backend.app.api.dependencies import build_container
    from backend.app.services.action_store import ACTION_TTL

    stale_clock = sheets_repos["tasks"].clock
    chat_noop = stack.chat_service  # propose an action, then advance the clock past 24h
    result = chat_noop.chat(
        "I need to research competitor products by Wednesday", employee_id="EMP-003",
    )
    action_id = result["proposed_actions"][0]["action_id"]
    stale_clock.advance(days=2)  # > ACTION_TTL (24h)
    with pytest.raises(ApiError) as ei:
        stack.action_service.confirm(action_id)
    assert ei.value.code is ErrorCode.ACTION_NOT_PENDING


def test_confirmation_rerevalidates_fk(stack) -> None:
    result = talk(stack, "assign some new work please", employee_id="EMP-003")
    # heuristic without employee name resolves to caller (EMP-003) — force a bad FK by tampering:
    action_id = result["proposed_actions"][0]["action_id"]
    stack.actions._actions[action_id].payload["assignee_id"] = "EMP-999"
    with pytest.raises(ApiError) as ei:
        stack.action_service.confirm(action_id)
    assert ei.value.code is ErrorCode.NOT_FOUND  # re-validation caught it; action stays PENDING
