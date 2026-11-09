"""Dependency-injection container (tasks T-012/T-080) — the ONLY place concrete adapters get wired.

- Storage: Google Sheets repositories when configured (B), else in-memory dev fallback (ADR-002).
- Model provider: selected here from settings (`MODEL_PROVIDER`); `auto` probes Ollama once and
  falls back to the graph's deterministic heuristics when it is not reachable. Strap-in for tests
  via the `provider` argument (MockModelProvider, docs/testing-strategy.md).
- Reconciliation loop: started in国民党 main.py lifespan when Sheets is configured (T-100).
- Voice: server-side transcription intentionally not wired in the MVP (route returns 501).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from backend.app.agent_wiring import build_agent_graph
from backend.app.core.config import Settings, get_settings
from backend.app.models.domain import Employee
from backend.app.services.action_service import ActionService
from backend.app.services.action_store import ActionStore
from backend.app.services.chat_service import ChatService
from backend.app.services.dashboard_service import DashboardService
from backend.app.services.meeting_service import MeetingService
from backend.app.services.memory import (
    MemoryActivityLogRepository,
    MemoryCommandLogRepository,
    MemoryEmployeeRepository,
    MemoryReminderRepository,
    MemoryTaskRepository,
)
from backend.app.services.reminder_service import ReminderService
from backend.app.services.task_service import TaskService
from backend.app.services.ports import (
    ActivityLogRepository,
    CommandLogRepository,
    EmployeeRepository,
    ReminderRepository,
    TaskRepository,
)
from backend.app.utils.ids import DEFAULT_CLOCK, Clock, to_iso

logger = logging.getLogger(__name__)

SEED_EMPLOYEES = [
    ("EMP-001", "Rahul", "rahul@example.com", "Engineer"),
    ("EMP-002", "Priya", "priya@example.com", "Designer"),
    ("EMP-003", "Aisha", "aisha@example.com", "Lead"),
]


@dataclass
class Container:
    settings: Settings
    tasks: TaskRepository
    employees: EmployeeRepository
    activity: ActivityLogRepository
    reminders: ReminderRepository
    commands: CommandLogRepository
    actions: ActionStore
    clock: Clock
    task_service: TaskService
    action_service: ActionService
    chat_service: ChatService
    reminders_service: ReminderService
    dashboard_service: DashboardService
    meeting_service: MeetingService
    sheets_available: bool = False
    graph: object | None = None
    reconciler: object | None = None

    def health_components(self) -> dict[str, str]:
        provider = getattr(self.graph, "provider", None)
        model_ok = "ok" if (provider is None or provider.is_available()) else "unavailable"
        return {
            "agent": "ok",
            "google_sheets": "ok" if self.sheets_available else "unavailable",
            "model_provider": model_ok,
            "voice": "ok",
        }


def build_container(
    settings: Settings | None = None,
    *,
    repos: tuple | None = None,
    clock: Clock | None = None,
    provider=None,
) -> Container:
    settings = settings or get_settings()
    clock = clock or DEFAULT_CLOCK

    # ---- storage backend selection (ADR-002: swappable via ports) ------------
    sheets_available = False
    if repos is not None:
        tasks, employees, activity, reminders, commands = repos  # test injection
    elif settings.sheets_configured:
        from integrations.google_sheets.repository import build_sheets_repositories

        tasks, employees, activity, reminders, commands = build_sheets_repositories(settings)
        sheets_available = True
    else:
        logger.warning(
            "Google Sheets not configured — using in-memory fallback (dev/test only; "
            "health reports google_sheets=unavailable per docs/api-contracts.md)."
        )
        activity = MemoryActivityLogRepository(clock=clock)
        employees = MemoryEmployeeRepository()
        tasks = MemoryTaskRepository(employees, activity, clock=clock)  # type: ignore[arg-type]
        reminders = MemoryReminderRepository(employees, activity, clock=clock)  # type: ignore[arg-type]
        commands = MemoryCommandLogRepository(clock=clock)
        for emp_id, name, email, role in SEED_EMPLOYEES:
            employees.add(
                Employee(
                    employee_id=emp_id, name=name, email=email, role=role,
                    created_at=to_iso(clock.utcnow()),
                )
            )

    actions = ActionStore(clock=clock)
    task_service = TaskService(tasks, employees)
    action_service = ActionService(actions, tasks, employees, reminders, activity, commands)
    graph = build_agent_graph(settings, provider_override=provider)
    chat_service = ChatService(graph, tasks, employees, activity, commands, actions, clock)
    reminders_service = ReminderService(reminders, task_service, activity, clock)
    dashboard_service = DashboardService(tasks, employees, activity, clock)
    meeting_service = MeetingService(tasks, employees, activity, actions, clock)
    return Container(
        settings=settings,
        tasks=tasks,
        employees=employees,
        activity=activity,
        reminders=reminders,
        commands=commands,
        actions=actions,
        clock=clock,
        task_service=task_service,
        action_service=action_service,
        chat_service=chat_service,
        reminders_service=reminders_service,
        dashboard_service=dashboard_service,
        meeting_service=meeting_service,
        sheets_available=sheets_available,
        graph=graph,
    )
