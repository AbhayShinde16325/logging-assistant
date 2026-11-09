"""Google Sheets repositories (scaffold — task T-023).

Implements the ports owned by Developer A in backend/app/services/ports.py:
TaskRepository, EmployeeRepository, ActivityLogRepository, ReminderRepository.
Stable IDs generated here (TASK-*/EMP-*/LOG-*/REM-*), row numbers never used as identity
(see integrations/AGENTS.md hard rules).
"""

from __future__ import annotations
