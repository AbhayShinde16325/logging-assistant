"""Duplicate-task detection & CRUD business rules (docs/testing-strategy.md)."""

import pytest

from backend.app.models.domain import Priority, RecordSource, TaskStatus
from backend.app.services.task_service import TaskService
from backend.app.utils.errors import ApiError, ErrorCode


@pytest.fixture()
def svc(sheets_repos):
    return TaskService(sheets_repos["tasks"], sheets_repos["employees"])


def test_create_task_and_fk_validation(svc, sheets_repos) -> None:
    task = svc.create_task(
        title="Research competitors", assignee_id="EMP-001", created_by="EMP-003",
        description="Competitor comparison", due_date="2026-11-11",
        priority=Priority.HIGH, source=RecordSource.CHAT,
    )
    assert task.task_id.startswith("TASK-")
    assert task.status == TaskStatus.TODO
    assert "Created task" in sheets_repos["activity"].list()[0][0].description


def test_unknown_assignee_is_entity_level_404(svc) -> None:
    with pytest.raises(ApiError) as ei:
        svc.create_task(title="x", assignee_id="EMP-999", created_by="EMP-001")
    assert ei.value.code is ErrorCode.NOT_FOUND and ei.value.status_code == 404


def test_open_duplicate_is_conflict(svc) -> None:
    svc.create_task(title="Competitor Research", assignee_id="EMP-001",
                    created_by="EMP-003", source=RecordSource.CHAT)
    with pytest.raises(ApiError) as ei:
        svc.create_task(title="  competitor   research  ", assignee_id="EMP-001",
                        created_by="EMP-003")
    assert ei.value.code is ErrorCode.CONFLICT and ei.value.status_code == 409


def test_done_task_is_not_a_duplicate(svc) -> None:
    t = svc.create_task(title="Competitor Research", assignee_id="EMP-001", created_by="EMP-003")
    svc.patch_task(t.task_id, {"status": TaskStatus.DONE}, source=RecordSource.CHAT)
    again = svc.create_task(title="competitor research", assignee_id="EMP-001", created_by="EMP-003")
    assert again.task_id != t.task_id


def test_patch_coerces_strings_and_validates_assignee(svc) -> None:
    t = svc.create_task(title="first", assignee_id="EMP-001", created_by="EMP-003")
    updated = svc.patch_task(t.task_id, {"status": "DONE", "priority": "high"},
                             source=RecordSource.API)
    assert updated.status == TaskStatus.DONE and updated.priority == Priority.HIGH
    with pytest.raises(ApiError):
        svc.patch_task(t.task_id, {"assignee_id": "EMP-999"}, source=RecordSource.API)


def test_delete_records_tombstone(svc, sheets_repos) -> None:
    t = svc.create_task(title="gone", assignee_id="EMP-001", created_by="EMP-003")
    svc.delete_task(t.task_id, source=RecordSource.API)
    assert sheets_repos["tasks"].get(t.task_id) is None
    entries, _ = sheets_repos["activity"].list(task_id=t.task_id)
    # activity list sorts by (timestamp, id); both entries share the fixed clock time so the
    # random LOG-xxx id tie-break makes order nondeterministic — assert the events, not the order.
    types = [e.activity_type.value for e in entries]
    assert "TASK_CREATED" in types and "TASK_DELETED" in types
