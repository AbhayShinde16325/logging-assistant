"""Opt-in end-to-end test against a REAL Google Spreadsheet (T-140).

Skipped unless BOTH are configured:
  GOOGLE_SHEET_TESTS_ENABLED=1
  GOOGLE_SHEETS_SPREADSHEET_ID=... + GOOGLE_APPLICATION_CREDENTIALS=<service-account json path>

Per skills/testing-and-integration/SKILL.md these are never part of the default pytest run
(no credentials on CI/dev boxes); failures here never block unit/contract runs. Cleanup: the
created task row is deleted again so repeated runs do not accumulate junk rows.
"""

from __future__ import annotations

import os

import pytest
from backend.app.models.domain import RecordSource, TaskStatus

ENABLED = os.getenv("GOOGLE_SHEET_TESTS_ENABLED", "") == "1"

pytestmark = pytest.mark.skipif(
    not ENABLED,
    reason="Set GOOGLE_SHEET_TESTS_ENABLED=1 + sheets credentials to run real-spreadsheet tests.",
)


@pytest.fixture(scope="module")
def real_repos():
    from backend.app.core.config import Settings

    from integrations.google_sheets.repository import build_sheets_repositories

    settings = Settings()
    assert settings.sheets_configured, "Credentials/spreadsheet env vars are missing."
    tasks, employees, activity, reminders, commands = build_sheets_repositories(settings)
    return {"tasks": tasks, "employees": employees, "activity": activity,
            "reminders": reminders, "commands": commands}


def test_task_crud_roundtrip(real_repos) -> None:
    tasks = real_repos["tasks"]
    task = tasks.create(
        title="E2E verification task", assignee_id="EMP-001", created_by="EMP-001",
        description="created by the opt-in integration test", source=RecordSource.API,
    )
    try:
        fetched = tasks.get(task.task_id)
        assert fetched is not None and fetched.title == "E2E verification task"
        updated = tasks.update(task.task_id, {"status": TaskStatus.DONE}, source=RecordSource.API)
        assert updated.status is TaskStatus.DONE
    finally:
        tasks.delete(task.task_id, source=RecordSource.API)
    assert tasks.get(task.task_id) is None


def test_employees_readable(real_repos) -> None:
    employees = real_repos["employees"].list()
    assert employees, "Employees tab must contain at least one row for the E2E test."


def test_activity_log_writes(real_repos) -> None:
    from backend.app.models.domain import ActivityType

    entry = real_repos["activity"].append(
        employee_id="EMP-001", task_id=None, activity_type=ActivityType.NOTE_SUBMITTED,
        description="integration-test note", source=RecordSource.API,
    )
    entries, _ = real_repos["activity"].list(employee_id="EMP-001", limit=50)
    assert any(e.activity_id == entry.activity_id for e in entries)
