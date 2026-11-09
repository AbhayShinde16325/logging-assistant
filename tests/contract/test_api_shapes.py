"""API response validation matrix (docs/testing-strategy.md "API response validation").

Every documented endpoint from docs/api-contracts.md is exercised for status codes, envelope
shapes and schema conformance — against the app as it would run (Sheets repo code over fakes).
"""

from __future__ import annotations

import pytest


# ---- auth / health --------------------------------------------------------------
def test_health_returns_component_map(client) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body["components"]) == {"agent", "google_sheets", "model_provider", "voice"}


def test_unknown_route_yields_envelope_404(client) -> None:
    resp = client.get("/api/v1/does_not_exist")
    assert resp.status_code == 404


# ---- chat -----------------------------------------------------------------------
def test_chat_requires_employee_when_multiple_exist(client) -> None:
    resp = client.post("/api/v1/chat", json={"message": "hello"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_with_unknown_employee_is_422(client) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "hello there", "employee_id": "EMP-999"},
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_chat_create_task_flow_shape(client) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "I need to research competitor products by Wednesday",
            "employee_id": "EMP-003",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["conversation_id"].startswith("CONV-")
    assert body["requires_confirmation"] is True
    assert body["message"], "assistant reply text required"
    (action,) = body["proposed_actions"]
    assert action["action_id"].startswith("ACT-")
    assert action["action_type"] == "CREATE_TASK"
    assert action["payload"]["assignee_id"] == "EMP-003"
    assert action["payload"]["due_date"] == "2026-11-11"


def test_chat_query_tasks_returns_result_without_confirmation(client) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "what are my pending tasks", "employee_id": "EMP-003"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["requires_confirmation"] is False
    assert body["result"]["total_open"] == 0


def test_chat_overlong_body_is_422(client) -> None:
    resp = client.post(
        "/api/v1/chat",
        json={"message": "x" * 2001, "employee_id": "EMP-003"},
    )
    assert resp.status_code == 422


# ---- confirm / reject -------------------------------------------------------------
def _propose(client) -> str:
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "I need to research competitor products by Wednesday",
            "employee_id": "EMP-003",
        },
    )
    return resp.json()["proposed_actions"][0]["action_id"]


def test_confirm_action_executes_and_returns_task(client) -> None:
    action_id = _propose(client)
    resp = client.post(f"/api/v1/actions/{action_id}/confirm")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "EXECUTED" and "task" in body["result"]


def test_confirm_after_reject_is_409(client) -> None:
    action_id = _propose(client)
    assert client.post(f"/api/v1/actions/{action_id}/reject").status_code == 200
    resp = client.post(f"/api/v1/actions/{action_id}/confirm")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ACTION_NOT_PENDING"


def test_reject_idempotency_violation_is_409(client) -> None:
    action_id = _propose(client)
    assert client.post(f"/api/v1/actions/{action_id}/reject").status_code == 200
    assert client.post(f"/api/v1/actions/{action_id}/reject").status_code == 409


def test_confirm_unknown_action_is_404(client) -> None:
    resp = client.post("/api/v1/actions/ACT-00000000/confirm")
    assert resp.status_code == 404


# ---- tasks CRUD -------------------------------------------------------------------
def test_task_crud_roundtrip(client) -> None:
    create = client.post("/api/v1/tasks", json={
        "title": "API-driven task", "assignee_id": "EMP-001",
        "status": "TODO", "priority": "HIGH", "due_date": "2026-11-20",
    })
    assert create.status_code == 201
    task = create.json()["task"]
    assert task["source"] == "API" and task["status"] == "TODO"

    got = client.get(f"/api/v1/tasks/{task['task_id']}")
    assert got.status_code == 200
    patched = client.patch(f"/api/v1/tasks/{task['task_id']}", json={"status": "DONE"})
    assert patched.status_code == 200 and patched.json()["task"]["status"] == "DONE"
    deleted = client.delete(f"/api/v1/tasks/{task['task_id']}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/tasks/{task['task_id']}").status_code == 404


def test_task_create_duplicate_conflict(client) -> None:
    body = {"title": "dup task", "assignee_id": "EMP-001", "priority": "LOW"}
    first = client.post("/api/v1/tasks", json=body)
    assert first.status_code == 201
    second = client.post("/api/v1/tasks", json=body)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"


def test_task_create_invalid_fields(client) -> None:
    bad = client.post("/api/v1/tasks", json={"title": "", "assignee_id": "EMP-999"})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "VALIDATION_ERROR"


def test_task_list_filters(client) -> None:
    client.post("/api/v1/tasks", json={
        "title": "alpha", "assignee_id": "EMP-001", "status": "TODO",
    })
    resp = client.get("/api/v1/tasks", params={"assignee_id": "EMP-001", "status": "TODO"})
    assert resp.status_code == 200
    assert all(t["assignee_id"] == "EMP-001" for t in resp.json()["tasks"])


# ---- employees --------------------------------------------------------------------
def test_employees_list_and_single(client) -> None:
    resp = client.get("/api/v1/employees")
    assert resp.status_code == 200
    rows = resp.json()["employees"]
    assert {e["employee_id"] for e in rows} == {"EMP-001", "EMP-002", "EMP-003"}
    one = client.get("/api/v1/employees/EMP-002")
    assert one.json()["employee"]["name"] == "Priya"
    assert client.get("/api/v1/employees/EMP-999").status_code == 404


# ---- activity ---------------------------------------------------------------------
def test_activity_requires_known_employee(client) -> None:
    resp = client.post("/api/v1/activity", json={
        "employee_id": "EMP-800",
        "activity_type": "NOTE_SUBMITTED",
        "description": "note",
        "source": "API",
    })
    assert resp.status_code == 404


def test_activity_post_and_list(client) -> None:
    create = client.post("/api/v1/activity", json={
        "employee_id": "EMP-001",
        "activity_type": "NOTE_SUBMITTED",
        "description": "worked late on the report",
        "source": "API",
    })
    assert create.status_code == 201
    listed = client.get("/api/v1/activity", params={"employee_id": "EMP-001"})
    assert listed.status_code == 200
    assert any(e["description"].startswith("worked late") for e in listed.json()["activity"])


# ---- voice ------------------------------------------------------------------------
def test_voice_transcribe_accepts_upload_contract_501(client) -> None:
    resp = client.post(
        "/api/v1/voice/transcribe?language=en",
        files={"audio": ("audio.webm", b"fake-bytes", "audio/webm")},
    )
    assert resp.status_code == 501
    assert resp.json()["error"]["code"] == "NOT_IMPLEMENTED_NOT_WIREABLE"


def test_voice_transcribe_rejects_bad_type(client) -> None:
    resp = client.post(
        "/api/v1/voice/transcribe",
        files={"audio": ("audio.mp3", b"by", "audio/mpeg")},
    )
    assert resp.status_code == 422


# ---- dashboard --------------------------------------------------------------------
def test_dashboard_summary_shape(client) -> None:
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body["team"]) >= {"total_open", "due_this_week", "overdue", "by_status"}
    assert {e["employee_id"] for e in body["employees"]} == {"EMP-001", "EMP-002", "EMP-003"}


# ---- meetings ---------------------------------------------------------------------
def test_meetings_extract_proposes_actions(client) -> None:
    notes = (
        "Action items:\n"
        "- Priya will prepare the design review by Friday\n"
        "- Decide pricing tiers\n"
    )
    resp = client.post("/api/v1/meetings/extract", json={
        "text": notes, "employee_id": "EMP-001", "date": "2026-11-09",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["requires_confirmation"] is True
    assert body["decisions"] or body["items"]
    for action in body["proposed_actions"]:
        assert action["action_type"] == "CREATE_TASK"


def test_meetings_extract_validation(client) -> None:
    assert client.post("/api/v1/meetings/extract", json={
        "text": "", "employee_id": "EMP-001",
    }).status_code == 422


# ---- reminders -------------------------------------------------------------------
def test_reminder_crud_flow(client) -> None:
    created = client.post("/api/v1/tasks", json={
        "title": "reminder host", "assignee_id": "EMP-001", "status": "TODO",
    })
    task = created.json()["task"]
    resp = client.post("/api/v1/reminders", json={
        "task_id": task["task_id"], "employee_id": "EMP-001",
        "scheduled_at": "2026-11-10T13:00:00.000Z",
    })
    assert resp.status_code == 201
    rem = resp.json()["reminder_id"]
    patch = client.patch(f"/api/v1/reminders/{rem}", json={"scheduled_at": "2026-11-10T05:00:00.000Z"})
    assert patch.status_code == 200
    listed = client.get("/api/v1/reminders", params={"task_id": task["task_id"]})
    assert listed.json()["reminders"][0]["status"] == "SCHEDULED"


def test_reminder_on_unknown_task_404(client) -> None:
    resp = client.post("/api/v1/reminders", json={
        "task_id": "TASK-00000000", "employee_id": "EMP-001",
        "scheduled_at": "2026-11-10T13:00:00.000Z",
    })
    assert resp.status_code == 404
