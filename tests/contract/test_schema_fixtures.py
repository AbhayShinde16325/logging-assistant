"""Contract schema fixtures (docs/testing-strategy.md).

Validates live API traffic against the canonical JSON Schemas in /contracts using the
`jsonschema` Draft 2020-12 validator, including cross-file $refs (chat-response → agent-action →
task) resolved through an in-memory registry. Payload shapes are additionally checked against the
corresponding `definitions.Payload*` subschema of agent-action.schema.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.validators import extend
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

CONTRACTS_DIR = Path(__file__).resolve().parents[2] / "contracts"
BASE = "https://contracts.local/"
_NAMES = ("agent-action", "chat-request", "chat-response", "task")


def _load(name: str) -> dict:
    doc = json.loads((CONTRACTS_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))
    doc["$id"] = BASE + name + ".schema.json"
    return doc


@pytest.fixture(scope="module")
def registry() -> Registry:
    reg: Registry = Registry()
    for name in _NAMES:
        doc = _load(name)
        resource = Resource.from_contents(doc, default_specification=DRAFT202012)
        reg = registry_resource(reg, BASE + name + ".schema.json", resource)
    return reg


def registry_resource(reg: Registry, uri: str, resource: Resource) -> Registry:
    return reg.with_resource(uri=uri, resource=resource)


def make_validator(schema: dict, reg: Registry) -> Draft202012Validator:
    return Draft202012Validator(schema, registry=reg)


# ---- chat request/response ---------------------------------------------------------
def test_chat_response_conforms(registry, client) -> None:
    chat_validator = make_validator(_load("chat-response"), registry)
    request_validator = make_validator(_load("chat-request"), registry)

    req = {"message": "I need to research competitor products by Wednesday",
           "employee_id": "EMP-003"}
    request_validator.validate(req)  # must not raise

    resp = client.post("/api/v1/chat", json=req).json()
    chat_validator.validate(resp)

    assert resp["requires_confirmation"] is True
    (action,) = resp["proposed_actions"]
    action_validator = make_validator(_load("agent-action"), registry)
    action_validator.validate(action)

    # payload validated against the per-type definition (top-level payload is generic)
    definitions = _load("agent-action")["definitions"]
    payload_validator = make_validator(definitions["PayloadCreateTask"], registry)
    payload_validator.validate(action["payload"])
    assert action["payload"]["due_date"] == "2026-11-11"


def test_task_resource_conforms(registry, client) -> None:
    task_validator = make_validator(_load("task"), registry)
    created = client.post("/api/v1/tasks", json={
        "title": "schema fixture task", "assignee_id": "EMP-001",
        "status": "TODO", "priority": "HIGH", "due_date": "2026-11-20",
    })
    assert created.status_code == 201
    task_validator.validate(created.json()["task"])

    fetched = client.get(f"/api/v1/tasks/{created.json()['task']['task_id']}").json()
    task_validator.validate(fetched["task"])

    listed = client.get("/api/v1/tasks", params={"assignee_id": "EMP-001"}).json()
    assert listed["total"] >= 1
    for t in listed["tasks"]:
        task_validator.validate(t)


def test_chat_query_result_shape(registry, client) -> None:
    chat_validator = make_validator(_load("chat-response"), registry)
    resp = client.post("/api/v1/chat", json={
        "message": "what are my pending tasks", "employee_id": "EMP-003",
    }).json()
    assert resp["requires_confirmation"] is False
    assert resp["proposed_actions"] == []
    chat_validator.validate(resp)


def test_reminder_proposal_payload_conforms(registry, client) -> None:
    container = client.app.state.container
    from backend.app.models.domain import RecordSource

    container.task_service.create_task(
        title="presentation draft", assignee_id="EMP-001", created_by="EMP-003",
        due_date="2026-11-13", source=RecordSource.CHAT,
    )
    body = client.post("/api/v1/chat", json={
        "message": "remind me about the presentation draft one day before the deadline",
        "employee_id": "EMP-003",
    }).json()
    (action,) = body["proposed_actions"]
    assert action["action_type"] == "CREATE_REMINDER"

    action_validator = make_validator(_load("agent-action"), registry)
    action_validator.validate(action)
    payload_validator = make_validator(_load("agent-action")["definitions"]["PayloadCreateReminder"], registry)
    payload_validator.validate(action["payload"])


def test_agent_action_id_format(registry, client) -> None:
    body = client.post("/api/v1/chat", json={
        "message": "I need to write the changelog by tomorrow", "employee_id": "EMP-003",
    }).json()
    (action,) = body["proposed_actions"]
    assert re.fullmatch(r"ACT-[0-9a-f]{8}", action["action_id"])
    assert re.fullmatch(r"CONV-[0-9a-f]{8}", body["conversation_id"])
