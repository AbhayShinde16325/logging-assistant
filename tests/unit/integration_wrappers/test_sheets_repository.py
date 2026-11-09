"""Google Sheets repository behaviors over FakeGoogleSheetsClient (docs/testing-strategy.md
"Google Sheets CRUD" + "manual spreadsheet changes" categories; fake-based, no credentials)."""

from __future__ import annotations

import pytest

from backend.app.models.domain import Priority, RecordSource, TaskStatus
from integrations.google_sheets import mapper
from integrations.google_sheets.repository import SheetsTaskRepository
from backend.app.utils.errors import ApiError, ErrorCode


@pytest.fixture()
def repo(sheets_repos):
    return sheets_repos["tasks"]


def test_crud_roundtrip(repo) -> None:
    task = repo.create(
        title="Competitor research", assignee_id="EMP-001", created_by="EMP-003",
        description="compare vendors", due_date="2026-11-11",
        priority=Priority.MEDIUM, source=RecordSource.CHAT,
    )
    fetch = repo.get(task.task_id)
    assert fetch.title == "Competitor research"
    items, total = repo.list_tasks(assignee_id="EMP-001", status=TaskStatus.TODO)
    assert total == 1 and items[0].task_id == task.task_id
    updated = repo.update(task.task_id, {"status": "DONE"}, source=RecordSource.CHAT)
    assert updated.status == TaskStatus.DONE
    assert repo.delete(task.task_id, source=RecordSource.API) is True
    assert repo.get(task.task_id) is None


def test_row_number_is_not_identity(repo) -> None:
    """Stable IDs survive reordering: get(task_id) keeps returning the right task even if
    someone manually inserts/pastes rows above it (docs/google-sheets-schema.md §2)."""
    t1 = repo.create(title="first", assignee_id="EMP-001", created_by="EMP-003")
    t2 = repo.create(title="second", assignee_id="EMP-002", created_by="EMP-003")
    client = sheets_client(repo)
    rows = client.all_rows(mapper.TAB_TASKS)
    # insert a new blank row ABOVE t1 in the raw sheet (row renumbering)
    rows[1:1] = [[""] * len(rows[0])]
    client.tabs[mapper.TAB_TASKS] = rows
    assert repo.get(t1.task_id).title == "first"
    assert repo.get(t2.task_id).title == "second"


def test_missing_row_not_found(repo) -> None:
    with pytest.raises(ApiError):
        repo.get_or_404("TASK-deadbeef")


def test_sheet_manual_row_deletion(repo) -> None:
    t = repo.create(title="soon gone", assignee_id="EMP-001", created_by="EMP-003")
    client = sheets_client(repo)
    # clear the row as a human edit would, then fetch — task unknown
    rows = client.get_rows(mapper.TAB_TASKS)
    for row in rows:
        if row[0] == t.task_id:
            row[:] = [""] * len(row)
    client.tabs[mapper.TAB_TASKS] = [client.tabs[mapper.TAB_TASKS][0]] + rows
    assert repo.get(t.task_id) is None


def test_invalid_rows_are_readable_not_fatal(repo) -> None:
    client = sheets_client(repo)
    client.append_row(mapper.TAB_TASKS, ["NOT-A-TASK-ID", "broken", "", "", "", "", "", "", "", "", "", "", ""])
    assert repo.list_tasks()  # no exception; invalid row skipped


def test_duplicate_task_id_keeps_first(repo) -> None:
    t = repo.create(title="first", assignee_id="EMP-001", created_by="EMP-003")
    rows = sheets_client(repo).all_rows(mapper.TAB_TASKS)
    rows.append(list(rows[1]))  # copy t1's row verbatim (duplicate ID)
    sheets_client(repo).tabs[mapper.TAB_TASKS] = rows
    assert repo.get(t.task_id).title == "first"


def sheets_client(repo: SheetsTaskRepository):
    return repo.client
