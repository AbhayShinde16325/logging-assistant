"""Shared test fixtures (tasks T-030, T-012): canonical fakes + app factory for contract tests.

Rules (skills/testing-and-integration/SKILL.md):
- ONE fake per interface; strategies in docs/testing-strategy.md are enforced here.
- FakeGoogleSheetsClient drives B's real repository code (rows/tabs behave like the real API).
- FakeClock makes reminder expiry, reconciliation guard windows and 24h action expiry deterministic.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.api import dependencies as deps
from backend.app.models.domain import Employee
from backend.app.services.memory import (
    MemoryActivityLogRepository,
    MemoryCommandLogRepository,
    MemoryEmployeeRepository,
    MemoryReminderRepository,
    MemoryTaskRepository,
)
from backend.app.utils.ids import DEFAULT_CLOCK, to_iso
from integrations.google_sheets.mapper import (
    TAB_ACTIVITY,
    TAB_COMMAND,
    TAB_EMPLOYEES,
    TAB_REMINDERS,
    TAB_TASKS,
    _ACTIVITY_HEADER,
    _COMMAND_HEADER,
    _EMP_HEADER,
    _REMINDER_HEADER,
    _TASK_HEADER,
)
from integrations.google_sheets.memory_client import MemorySheetsClient
from integrations.google_sheets.reconciliation import ReconciliationWorker
from integrations.google_sheets.repository import (
    SheetsActivityLogRepository,
    SheetsCommandLogRepository,
    SheetsEmployeeRepository,
    SheetsReminderRepository,
    SheetsTaskRepository,
)


SEED_TIME = datetime(2026, 11, 9, 9, 0, 0, tzinfo=timezone.utc)


@pytest.fixture()
def seed_time() -> datetime:
    """Fixed 'today' used everywhere (LLM-free, deterministic)."""
    return SEED_TIME


class FakeClock:
    """Deterministic clock matching backend.app.utils.ids.Clock (injected everywhere)."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def utcnow(self) -> datetime:
        return self._now

    def advance(self, **delta) -> None:
        self._now = self._now + timedelta(**delta)

    def advance_to(self, when: datetime) -> None:
        self._now = when


@pytest.fixture()
def fake_clock(seed_time) -> FakeClock:
    return FakeClock(seed_time)


class FakeGoogleSheetsClient(MemorySheetsClient):
    """Canonical fake for the Sheets client — the ONLY one (T-030).

    Simulates the real API's row-level surface for the 5 canonical tabs: headers + seeded
    employees (Rahul/Priya/Aisha) as if maintained manually, manual edits via set_row(),
    physical delete via clear_row() (blank).
    """

    def __init__(self) -> None:
        super().__init__({})
        self._ensure(TAB_EMPLOYEES, header=_EMP_HEADER)
        self._ensure(TAB_TASKS, header=_TASK_HEADER)
        self._ensure(TAB_ACTIVITY, header=_ACTIVITY_HEADER)
        self._ensure(TAB_REMINDERS, header=_REMINDER_HEADER)
        self._ensure(TAB_COMMAND, header=_COMMAND_HEADER)
        for emp_id, name, role in (
            ("EMP-001", "Rahul", "Engineer"),
            ("EMP-002", "Priya", "Engineer"),
            ("EMP-003", "Aisha", "Lead"),
        ):
            self.append_row(TAB_EMPLOYEES,
                            [emp_id, name, f"{emp_id.lower()}@example.com", role,
                             "2026-11-01T09:00:00.000Z"],
                            skip_header=True)


@pytest.fixture()
def sheets_stack():
    """B's real repository code over the canonical fake client (contract-first, no credentials)."""
    activity = SheetsActivityLogRepository(client=object())
    del activity  # rebuilt below over the fake client (typing detail in repository.py)
    yield None  # actual stack fixture contained in sheets_repos


@pytest.fixture()
def sheets_repos(fake_clock):
    client = FakeGoogleSheetsClient()
    activity = SheetsActivityLogRepository(client, clock=fake_clock)
    employees_repo = SheetsEmployeeRepository(client)
    tasks_repo = SheetsTaskRepository(client, employees_repo, activity, clock=fake_clock)
    reminders_repo = SheetsReminderRepository(client, activity, clock=fake_clock)
    commands_repo = SheetsCommandLogRepository(client, clock=fake_clock)
    return {
        "client": client,
        "tasks": tasks_repo,
        "employees": employees_repo,
        "activity": activity,
        "reminders": reminders_repo,
        "commands": commands_repo,
    }


@pytest.fixture()
def three_employees() -> list[Employee]:
    return [Employee(
        employee_id=e[0], name=e[1], email=e[2], role=e[3],
        created_at=to_iso(DEFAULT_CLOCK.utcnow()),
    ) for e in (
        ("EMP-001", "Rahul", "rahul@example.com", "Engineer"),
        ("EMP-002", "Priya", "priya@example.com", "Engineer"),
        ("EMP-003", "Aisha", "aisha@example.com", "Lead"),
    )]


@pytest.fixture()
def memory_repos(three_employees, fake_clock):
    activity = MemoryActivityLogRepository(clock=fake_clock)
    employees = MemoryEmployeeRepository(three_employees)
    tasks = MemoryTaskRepository(employees, activity, clock=fake_clock)
    reminders = MemoryReminderRepository(employees, activity, clock=fake_clock)
    commands = MemoryCommandLogRepository(clock=fake_clock)
    return {
        "tasks": tasks, "employees": employees, "activity": activity,
        "reminders": reminders, "commands": commands,
    }


@pytest.yield_fixture()  # keep legacy style for compat across the dev box
def test_settings():
    """Test-mode settings: no Ollama probing; deterministic heuristic agent (model path is
    exercised separately via MockModelProvider fixtures)."""
    from backend.app.core.config import Settings

    return Settings(app_env="test", model_provider="heuristic", log_level="ERROR")


@pytest.yield_fixture()  # keep legacy style for compat across the dev box
def sheets_container(sheets_repos, fake_clock, test_settings):
    """Full backend app container wired over Sheets repos + fake client (T-080 contract style)."""
    container = deps.build_container(
        settings=test_settings,
        repos=(
            sheets_repos["tasks"], sheets_repos["employees"], sheets_repos["activity"],
            sheets_repos["reminders"], sheets_repos["commands"],
        ),
        clock=fake_clock,
        provider=None,
    )
    yield container


@pytest.fixture()
def reconciliation_worker(sheets_repos, fake_clock):
    """Reconciliation worker over the fake client (T-100 tests)."""
    return ReconciliationWorker(
        client=sheets_repos["client"],
        activity_repo=sheets_repos["activity"],
        clock=fake_clock,
        poll_interval=60,
    )
