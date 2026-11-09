"""Dependency-injection wiring (scaffold — task T-012, final wiring T-080).

Provides FastAPI dependencies that hand out the ports defined in app.services.ports:
- TaskRepository / EmployeeRepository / ActivityLogRepository / ReminderRepository — concrete adapters injected ONLY here
- Transcriber (from the voice module)
- The agent graph callable

Never import concrete Google/Ollama classes from route modules — they get these dependencies.
"""

from __future__ import annotations
