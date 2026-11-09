"""Reconciliation behaviors (T-100, docs/google-sheets-schema.md §3): manual-edit detection,
conflict precedence (manual wins), self-write guard window, missing row detection."""

from __future__ import annotations

from datetime import timedelta

from backend.app.models.domain import RecordSource
from backend.app.utils.ids import parse_iso, to_iso
from integrations.google_sheets.mapper import TAB_TASKS


def test_manual_edit_detected(reconciliation_worker, sheets_repos, fake_clock) -> None:
    repo = sheets_repos["tasks"]
    task = repo.create(title="Original title", assignee_id="EMP-001", created_by="EMP-003",
                       source=RecordSource.CHAT)
    worker = reconciliation_worker
    fake_clock.advance(minutes=1)  # create's updated_at leaves the 5s self-write guard
    worker.poll_once()  # seed baseline (first poll reports the row as new — discarded)

    # a HUMAN edits value in the sheet directly (updated_at column untouched)
    rows = sheets_repos["client"].all_rows(TAB_TASKS)
    for row in rows:
        if row[0] == task.task_id:
            row[1] = "renamed in the sheet"
    sheets_repos["client"].tabs[TAB_TASKS] = rows

    changes = worker.poll_once()
    assert any(c.task_id == task.task_id and c.field == "title" for c in changes)
    entries, _ = sheets_repos["activity"].list()
    assert any(e.activity_type.value == "MANUAL_SHEET_EDIT" for e in entries)


def test_app_own_write_is_not_flagged(reconciliation_worker, sheets_repos, fake_clock) -> None:
    repo = sheets_repos["tasks"]
    task = repo.create(title="First", assignee_id="EMP-001", created_by="EMP-003",
                       source=RecordSource.API)
    worker = reconciliation_worker
    worker.poll_once()  # baseline
    # the APP updates through the repository (updated_at = now, inside guard window)
    repo.update(task.task_id, {"title": "Renamed by the app"}, source=RecordSource.API)
    assert worker.poll_once() == []


def test_manual_row_deletion_detected(reconciliation_worker, sheets_repos, fake_clock) -> None:
    repo = sheets_repos["tasks"]
    task = repo.create(title="vanishing", assignee_id="EMP-001", created_by="EMP-003",
                       source=RecordSource.CHAT)
    worker = reconciliation_worker
    worker.poll_once()
    # human deletes the row entirely
    rows = sheets_repos["client"].all_rows(TAB_TASKS)
    filtered = [rows[0]] + [r for r in rows[1:] if r[0] != task.task_id]
    sheets_repos["client"].tabs[TAB_TASKS] = filtered
    changes = worker.poll_once()
    assert any(c.task_id == task.task_id and c.to_value == " deleted" for c in changes)
    entries, _ = sheets_repos["activity"].list()
    assert any("row deleted" in e.description for e in entries)


def test_manual_row_insertion_snapshot(reconciliation_worker, sheets_repos, fake_clock) -> None:
    worker = reconciliation_worker
    worker.poll_once()  # baseline
    repo = sheets_repos["tasks"]
    task = repo.create(title="New task from another user", assignee_id="EMP-002",
                       created_by="EMP-003", source=RecordSource.MANUAL_SHEET)
    changes = worker.poll_once()
    assert any(c.task_id == task.task_id and c.to_value == "new" for c in changes)


def test_conflict_precedence_manual_wins(reconciliation_worker, sheets_repos, fake_clock) -> None:
    """Per docs/google-sheets-schema.md §3: when a manual edit and an app write collide on the
    same row, the manual edit wins the row's content. The app re-validates pending actions
    against the reconciled state at confirm time (test_action_lifecycle covers confirmation)."""
    repo = sheets_repos["tasks"]
    task = repo.create(title="before", assignee_id="EMP-001", created_by="EMP-003")
    worker = reconciliation_worker
    fake_clock.advance(minutes=1)  # leave the self-write guard window
    worker.poll_once()
    rows = sheets_repos["client"].all_rows(TAB_TASKS)
    for row in rows:
        if row[0] == task.task_id:
            row[1] = "manual-state"
            row[9] = to_iso(fake_clock.utcnow() - timedelta(days=3))  # backdated → manual signal
    sheets_repos["client"].tabs[TAB_TASKS] = rows
    changes = worker.poll_once()
    assert changes, "backdated update must be treated as a manual edit"
    assert repo.get(task.task_id).title == "manual-state"
