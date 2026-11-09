"""End-to-end contract flows (docs/testing-strategy.md "API response validation"):

chat → propose → confirm/reject → repository rows (real Sheets repository code over the
canonical fake client) → Activity_Log / Command_Log. No LLM involved (heuristic path).
"""

from __future__ import annotations

from datetime import timedelta

from backend.app.models.domain import ActivityType, RecordSource, ReminderStatus, TaskStatus
from backend.app.services.reminder_service import to_iso_utc


def _chat(client, message: str, employee_id: str = "EMP-003"):
    resp = client.post("/api/v1/chat", json={"message": message, "employee_id": employee_id})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _confirm(client, action_id: str):
    resp = client.post(f"/api/v1/actions/{action_id}/confirm")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _activity_types(container, task_id: str) -> list[str]:
    entries, _ = container.activity.list(task_id=task_id)
    return [e.activity_type.value for e in entries]


def test_confirm_creates_task_row_logs_and_updates_command(client) -> None:
    container = client.app.state.container
    body = _chat(client, "I need to research competitor products by Wednesday")
    (action,) = body["proposed_actions"]
    action_id = action["action_id"]

    result = _confirm(client, action_id)
    assert result["status"] == "EXECUTED"
    task = result["result"]["task"]
    assert task["status"] == "TODO"

    # Task row exists in the (fake) sheet through B's real repository code
    stored = container.tasks.get(task["task_id"])
    assert stored is not None and stored.title == "research competitor products"

    # Activity_Log has TASK_CREATED (T-060)
    assert ActivityType.TASK_CREATED.value in _activity_types(container, task["task_id"])

    # Command_Log row flipped to CONFIRMED with the executed action id (T-062)
    rows = container.commands.client.get_rows("Command_Log")
    ours = [r for r in rows if r and r[7] == action_id]
    assert ours and ours[0][6] == "CONFIRMED"


def test_reject_creates_nothing_but_logs(client) -> None:
    container = client.app.state.container
    body = _chat(client, "I need to ship the beta on Friday")
    action_id = body["proposed_actions"][0]["action_id"]
    tasks_before, _ = container.tasks.list_tasks()

    resp = client.post(f"/api/v1/actions/{action_id}/reject")
    assert resp.status_code == 200 and resp.json()["status"] == "REJECTED"

    tasks_after, _ = container.tasks.list_tasks()
    assert tasks_after == tasks_before  # no state change on reject

    rows = container.commands.client.get_rows("Command_Log")
    ours = [r for r in rows if r and r[7] == action_id]
    assert ours and ours[0][6] == "REJECTED"


def test_complete_task_flow_sets_done(client) -> None:
    container = client.app.state.container
    task = container.task_service.create_task(
        title="authentication module", assignee_id="EMP-001", created_by="EMP-003",
        source=RecordSource.CHAT,
    )
    body = _chat(client, "I completed the authentication module")
    (action,) = body["proposed_actions"]
    assert action["action_type"] == "COMPLETE_TASK"
    result = _confirm(client, action["action_id"])
    assert result["result"]["task"]["status"] == "DONE"
    assert container.tasks.get(task.task_id).status == TaskStatus.DONE
    assert ActivityType.TASK_COMPLETED.value in _activity_types(container, task.task_id)


def test_assign_new_task_to_named_employee(client) -> None:
    container = client.app.state.container
    body = _chat(client, "assign competitor research to Priya")
    (action,) = body["proposed_actions"]
    assert action["payload"]["assignee_id"] == "EMP-002"
    result = _confirm(client, action["action_id"])
    assert result["result"]["task"]["assignee_id"] == "EMP-002"


def test_reminder_flow_uses_task_deadline(client) -> None:
    container = client.app.state.container
    task = container.task_service.create_task(
        title="quarterly report", assignee_id="EMP-001", created_by="EMP-003",
        due_date="2026-11-11", source=RecordSource.CHAT,
    )
    body = _chat(client, "remind me about the quarterly report two hours before the deadline")
    (action,) = body["proposed_actions"]
    assert action["action_type"] == "CREATE_REMINDER"
    result = _confirm(client, action["action_id"])
    scheduled = result["result"]["reminder"]["scheduled_at"]
    assert scheduled.startswith("2026-11-11T07:00")

    reminders = container.reminders.list(task_id=task.task_id)
    assert [r.status for r in reminders] == [ReminderStatus.SCHEDULED]
    assert reminders[0].scheduled_at == scheduled


def test_reminder_fires_on_scheduler_tick(client) -> None:
    container = client.app.state.container
    task = container.task_service.create_task(
        title="standup feed", assignee_id="EMP-002", created_by="EMP-003",
        due_date="2026-11-12", source=RecordSource.CHAT,
    )
    rem = container.reminders_service.create(
        task_id=task.task_id, employee_id="EMP-002",
        scheduled_at=to_iso_utc(container.clock.utcnow() + timedelta(hours=1)),
    )
    container.reminders_service.process_due()  # nothing due yet
    assert container.reminders.get(rem.reminder_id).status == ReminderStatus.SCHEDULED
    container.clock.advance(hours=2)
    container.reminders_service.process_due()
    assert container.reminders.get(rem.reminder_id).status == ReminderStatus.SENT
