"""Dashboard summary (T-081): statistics derive from the repositories, never model memory."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from backend.app.models.domain import TaskStatus
from backend.app.services.ports import (
    ActivityLogRepository,
    EmployeeRepository,
    TaskRepository,
)
from backend.app.utils.ids import Clock, to_iso

OPEN_STATUSES = (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED)
SEVEN_DAYS = timedelta(days=7)
DAY = timedelta(days=1)


class DashboardService:
    def __init__(
        self,
        tasks: TaskRepository,
        employees: EmployeeRepository,
        activity: ActivityLogRepository,
        clock: Clock,
    ) -> None:
        self.tasks = tasks
        self.employees = employees
        self.activity = activity
        self.clock = clock

    def summary(self) -> dict[str, Any]:
        today_iso = self.clock.utcnow().date().isoformat()
        week_ago_iso = to_iso(self.clock.utcnow() - timedelta(days=7))
        all_tasks, total = self.tasks.list_tasks(limit=1000)

        by_status: dict[str, int] = {}
        for t in all_tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1

        due_this_week_items = [t for t in all_tasks if t.due_date and t.status in OPEN_STATUSES
                               and today_iso <= t.due_date <= (self.clock.utcnow().date() + timedelta(days=7)).isoformat()]
        overdue_items = [t for t in all_tasks if t.due_date and t.due_date < today_iso
                         and t.status in OPEN_STATUSES]

        entries, _ = self.activity.list(limit=1000)
        # completed per employee over last 7 days: TASK_CREATED + TASK_COMPLETED in activity
        completed_recent = {
            e.employee_id: 0 for e in self.employees.list()
        }
        for e in entries:
            if e.activity_type.value == "TASK_COMPLETED" and e.timestamp >= week_ago_iso:
                completed_recent[e.employee_id] = completed_recent.get(e.employee_id, 0) + 1

        employee_rows: list[dict[str, Any]] = []
        for emp in self.employees.list():
            mine = [t for t in all_tasks if t.assignee_id == emp.employee_id]
            employee_rows.append(
                {
                    "employee_id": emp.employee_id,
                    "name": emp.name,
                    "open_tasks": sum(1 for t in mine if t.status in OPEN_STATUSES),
                    "overdue": sum(1 for t in mine if t.status in OPEN_STATUSES and t.due_date
                                   and t.due_date < today_iso),
                    "completed_7d": completed_recent.get(emp.employee_id, 0),
                }
            )

        return {
            "team": {
                "total_open": sum(1 for t in all_tasks if t.status in OPEN_STATUSES),
                "due_this_week": len(due_this_week_items),
                "overdue": len(overdue_items),
                "completed_7d": sum(completed_recent.values()),
                "by_status": by_status,
            },
            "employees": employee_rows,
        }

