# Requirements — MVP (v1.0, baseline for Milestone 0 sign-off)

These requirements are the baseline agreed by the team before implementation. Any change must be
proposed in an ADR (`docs/decisions/`) and reflected here + in `tasks.md`.

## 1. Functional requirements

### FR — Interaction

| ID | Requirement | Priority | Verification |
|----|-------------|----------|--------------|
| FR-1 | User interacts with the assistant in typed natural language via a chat interface. | P0 | Chat UI round-trip demo |
| FR-2 | User can dictate instructions via browser voice input; speech becomes text before the agent runs (transcription is separate from orchestration). | P1 | Voice-path demo |
| FR-3 | Before executing any consequential operation (create/update/delete/assign task, create reminder), the assistant asks for explicit confirm/reject. | P0 | Confirmation flow test |
| FR-4 | Read-only queries (list tasks, summarize activity) do **not** require confirmation. | P0 | Agent workflow test |

### FR — Tasks

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10 | Extract task intent from natural language: title, due date, assignee, priority (default MEDIUM), description. | P0 |
| FR-11 | Create tasks in the shared store (Google Sheets `Tasks` tab) with a stable unique `task_id`. | P0 |
| FR-12 | Assign a task to an existing employee by name or ID, resolved/validated by the backend (never trusted from the LLM alone). | P0 |
| FR-13 | Modify a task (title, description, assignee, priority, due date). | P0 |
| FR-14 | Mark a task completed; status enum: `TODO, IN_PROGRESS, BLOCKED, DONE, CANCELLED`. | P0 |
| FR-15 | List tasks filtered by assignee/status/date, sorted by due date; employee-wise views. | P0 |
| FR-16 | Prevent accidental duplicate task creation (title + assignee + open-status near-match check before confirming). | P1 |
| FR-17 | Delete a task (soft-confirmed; logged). | P1 |

### FR — Employees

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-20 | Employee records live in the `Employees` tab: employee_id, name, email, role, created_at. | P0 |
| FR-21 | "Me"/pronouns resolve against the `employee_id` supplied by the frontend session. | P0 |
| FR-22 | Other employees referred to by name are resolved via lookup; ambiguity triggers clarification, not a guess. | P0 |

### FR — Tracking, activity, reminders

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-30 | Every state-changing operation writes an Activity_Log entry (who, what, when, source). | P1 |
| FR-31 | Manual edits in the sheet are detected (polling, ~60s) and reconciled; app-created rows are distinguishable from manual edits. | P1 |
| FR-32 | Users can schedule task reminders ("two hours before the deadline") stored in `Reminders`; a scheduler loop marks them `DUE`/`SENT` while the backend runs. | P1 |
| FR-33 | Meeting notes/transcripts pasted into the assistant produce extracted actions — tasks, decisions, action items — for individual confirmation. | P2 |
| FR-34 | Dashboard endpoint returns team + per-employee task statistics; frontend renders a basic dashboard. | P1 |

## 2. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | All API payloads validated with Pydantic; all responses use the standard error envelope. |
| NFR-2 | Latency: agent reply within ~10s locally (Ollama, timeout 60s, 1 retry). |
| NFR-3 | No secrets in the repo; `.env` + service-account JSON are gitignored and stay outside. |
| NFR-4 | The prototype is safe for a small internal team — shared optional bearer token only. Explicitly **not** production-grade security. |
| NFR-5 | Unit tests mock LLM + Google Sheets; real integration tests are opt-in via env flag with credentials. |
| NFR-6 | Runs on consumer laptops: Python 3.11, Node 18+, Ollama with a ~8B instruct model. |
| NFR-7 | Cost: open-source/local-first; no paid API as mandatory dependency. |

## 3. MVP workflow (the one demo that matters)

```text
1. User: "Assign competitor research to me by Wednesday."
2. Agent: intent=CREATE_TASK → structured action ACT-… (validated, employee resolved)
3. Assistant: proposes the task → requires_confirmation: true
4. User confirms → POST /api/v1/actions/{id}/confirm
5. Backend validates → Google Sheets Tasks row created → Activity_Log entry → response
6. User may also say "Remind me one day before the deadline" → Reminders row
```

## 4. Out of scope (MVP)

- Multi-team / multi-tenant support, SSO, granular RBAC.
- PostgreSQL / Redis / queues; Google Calendar; email/Slack notifications.
- Automatic meeting joining or recording (the platform would violate trust & ToS assumptions).
- Mobile apps; offline mode; historical analytics.
