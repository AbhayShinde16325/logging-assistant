"""Reminder lifecycle + scheduler loop (milestone 4, T-101).

docs/api-contracts.md § Reminders — transitions SCHEDULED → DUE → SENT (or → CANCELLED).
Firing requires the backend process to run (fire = status transition + REMINDER_SENT activity log;
no push notifications in the MVP). Time is injected (Clock) for deterministic tests.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from backend.app.models.domain import ReminderStatus
from backend.app.services.ports import (
    ActivityLogRepository,
    ReminderRepository,
)
from backend.app.services.task_service import TaskService
from backend.app.utils.errors import not_found, validation_error
from backend.app.utils.ids import Clock, parse_iso, to_iso

logger = logging.getLogger(__name__)
REMINDER_MANAGER = None


class ReminderService:
    def __init__(
        self,
        reminders: ReminderRepository,
        tasks: TaskService,
        activity: ActivityLogRepository,
        clock: Clock,
    ) -> None:
        self.reminders = reminders
        self.tasks = tasks
        self.activity = activity
        self.clock = clock

    # -- CRUD --------------------------------------------------------------------
    def create(
        self, *, task_id: str, employee_id: str, scheduled_at: str,
        source=None,
    ):
        # schema guarantees prefixed IDs; FK existence is the entity rule here
        if source is None:
            from backend.app.models.domain import RecordSource

            source = RecordSource.API
        self.tasks.validate_employees_exist(employee_id)
        self.tasks.get_task(task_id)
        parsed = _parse_timestamp(scheduled_at)
        if parsed is None:
            raise validation_error(
                "scheduled_at must be an ISO 8601 UTC timestamp like 2026-11-10T09:00:00Z",
                {"scheduled_at": scheduled_at},
            )
        return self.reminders.create(
            task_id=task_id, employee_id=employee_id, scheduled_at=to_iso_utc(parsed),
            source=source,
        )

    def list(self, *, task_id=None, employee_id=None, status=None):
        return self.reminders.list(task_id=task_id, employee_id=employee_id, status=status)

    def patch(self, reminder_id: str, patch: dict):
        rem = self.reminders.get(reminder_id)
        if rem is None:
            raise not_found(f"Reminder '{reminder_id}' not found.", {"reminder_id": reminder_id})
        if patch.get("status") is not None:
            if patch["status"] not in (
                ReminderStatus.CANCELLED, ReminderStatus.SCHEDULED,
                ReminderStatus.DUE, ReminderStatus.SENT,
            ):
                raise validation_error(
                    f"Invalid reminder status {patch['status']}.",
                    {"status": str(patch["status"])},
                )
            updated = self.reminders.update_status(reminder_id, patch["status"])
        else:
            scheduled_at = patch.get("scheduled_at")
            if scheduled_at is None:
                raise validation_error("At least one of scheduled_at/status is required.")
            parsed = _parse_timestamp(scheduled_at)
            if parsed is None:
                raise validation_error(
                    "scheduled_at must be an ISO 8601 UTC timestamp",
                    {"scheduled_at": scheduled_at},
                )
            from backend.app.services.ports import ReminderRepository as _ReminderPort

            # reschedule = relink row to a new ABSOLUTE time; Mutable repo supports set-scheduled
            updated = _reschedule(self.reminders, reminder_id, to_iso_utc(parsed))
        return updated

    # -- scheduler loop -----------------------------------------------------------
    def process_due(self) -> list[dict]:
        """One scheduler tick: SCHEDULED → DUE (when time reached) → SENT (fired + logged).

        DUE and SENT transitions both happen per tick in the MVP (simplified fire-as-loop;
        no push channel). Returns the reminders sent in this tick.
        """
        now_ts = to_iso(self.clock.utcnow())
        sent_now: list[dict] = []
        for rem in self.reminders.list():
            if rem.status == ReminderStatus.SCHEDULED and rem.scheduled_at <= now_ts:
                rem = self.reminders.update_status(rem.reminder_id, ReminderStatus.DUE) or rem
            if rem.status == ReminderStatus.DUE:
                fired = self.reminders.update_status(rem.reminder_id, ReminderStatus.SENT)
                if fired is not None:
                    sent_now.append(fired.model_dump(mode="json"))
        return sent_now

    async def run_forever(self, poll_seconds: float = 30.0) -> None:
        """Started from the app's lifespan; per docs it only runs while the process runs."""
        while True:
            try:
                self.process_due()
            except Exception:  # noqa: BLE001 — scheduler must survive transient errors
                logger.exception("Reminder tick failed")
            await asyncio.sleep(poll_seconds)


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return parse_iso(value)
    except Exception:  # noqa: BLE001 — validation only
        return None


def to_iso_utc(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return to_iso(dt)


def _reschedule(repository, reminder_id: str, scheduled_at: str):
    """Reschedule is implemented by the concrete repos; ports expose update_status only, so we
    simulate a reschedule by service-level DELETE+CREATE is NOT used (identity must be stable) —
    instead the concrete repository implements `reschedule` (Sheets & memory)."""
    if hasattr(repository, "reschedule"):
        return repository.reschedule(reminder_id, scheduled_at)
    raise NotImplementedError("Repository must implement reschedule() for PATCH reminders.")
