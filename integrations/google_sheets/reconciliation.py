"""Manual-edit reconciliation (task T-100) — docs/google-sheets-schema.md §3 rules.

Poll worker (callable provided to the backend; the backend owns the loop lifecycle):
- Snapshot-compare each poll. Manual edits = content drift WITHOUT a matching app write
  (updated_at stale/absent/mismatch vs cache).
- Self-write guard: rows whose updated_at is within GUARD_SECONDS of the poll are ignored
  (they may be our own in-flight writes flushing).
- Conflict rule: the manual edit wins the row's content; the app re-validates any PENDING
  action against the new state at confirm time (docs/api-contracts.md).
- Detection writes a MANUAL_SHEET_EDIT activity row and returns a snapshot back to the backend.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta, timezone
from typing import Any

from backend.app.models.domain import ActivityType, RecordSource
from backend.app.utils.ids import Clock
from backend.app.utils.ids import DEFAULT_CLOCK, parse_iso, to_iso

from . import mapper

logger = logging.getLogger("integrations.reconciliation")

GUARD_SECONDS = 5  # docs/google-sheets-schema.md §3 guard window


@dataclass
class ReconciliationChange:
    tab: str
    task_id: str | None
    field: str | None
    from_value: str | None
    to_value: str | None


@dataclass
class SyncSnapshot:
    rows: dict[str, dict[str, str]] = field(default_factory=dict)
    last_polled: str | None = None


class ReconciliationWorker:
    def __init__(
        self,
        client: Any,
        activity_repo,
        clock: Clock = DEFAULT_CLOCK,
        poll_interval: int = 60,
    ) -> None:
        self.client = client
        self.activity = activity_repo
        self.clock = clock
        self.poll_interval = poll_interval
        self.state = SyncSnapshot()

    def poll_once(self) -> list[ReconciliationChange]:
        changes = self._detect_task_changes()
        self.state.rows = self._snapshot_tasks()
        self.state.last_polled = to_iso(self.clock.utcnow())
        return changes

    def _snapshot_tasks(self) -> dict[str, dict[str, str]]:
        rows = self.client.get_rows(mapper.TAB_TASKS)
        out: dict[str, dict[str, str]] = {}
        for row in rows:
            if len(row) < len(mapper._TASK_HEADER):
                row = list(row) + [""] * (len(mapper._TASK_HEADER) - len(row))
            task_id = str(row[0]).strip() if row and row[0] else None
            if not task_id:
                continue
            out[task_id] = {
                "title": str(row[1]).strip(),
                "description": str(row[2]).strip(),
                "assignee_id": str(row[3]).strip(),
                "status": str(row[5]).strip().upper(),
                "priority": str(row[6]).strip().upper(),
                "due_date": str(row[7]).strip(),
                "updated_at": str(row[9]).strip(),
                "source": str(row[10]).strip().upper(),
            }
        return out

    def _detect_task_changes(self) -> list[ReconciliationChange]:
        current = self._snapshot_tasks()
        previous = self.state.rows
        changes: list[ReconciliationChange] = []
        now = self.clock.utcnow()

        for task_id, before in previous.items():
            if task_id not in current:
                changes.append(ReconciliationChange("Tasks", task_id, None, "present", " deleted"))
                self._log(task_id, "Removed manually in sheet (row deleted).")
                continue
            after = current[task_id]
            # self-write guard: our own recent write isn't a manual edit
            if self._within_guard(before["updated_at"], now):
                continue
            drifted = {
                k for k in ("title", "description", "assignee_id", "status", "priority", "due_date")
                if before[k] != after[k]
            }
            if not drifted:
                continue
            for k in drifted:
                changes.append(
                    ReconciliationChange("Tasks", task_id, k, before[k], after[k])
                )
                self._log(
                    task_id,
                    f"Manual sheet edit on '{k}': '{before[k]}' → '{after[k]}'.",
                )

        # new rows appear without a cached prior state (e.g. seeded manually)
        for task_id in current:
            if task_id not in previous:
                changes.append(
                    ReconciliationChange("Tasks", task_id, None, "absent", "new")
                )
                self._log(task_id, "New row found during reconciliation snapshot.")
        return changes

    def _within_guard(self, updated_at: str, now: Any) -> bool:
        if not updated_at:
            return False
        try:
            ts = parse_iso(updated_at)
        except Exception:  # noqa: BLE001 — unparseable timestamps de-optimize to false (manual)
            return False
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return abs((now - ts).total_seconds()) <= GUARD_SECONDS

    def _log(self, task_id: str | None, description: str) -> None:
        try:
            self.activity.append(
                employee_id=task_id or "UNKNOWN",
                task_id=task_id,
                activity_type=ActivityType.MANUAL_SHEET_EDIT,
                description=description[:500],
                source=RecordSource.MANUAL_SHEET,
            )
        except Exception:  # noqa: BLE001 — logging must not break reconciliation
            logger.exception("Failed to write MANUAL_SHEET_EDIT activity")
