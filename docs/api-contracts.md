# API Contracts — `/api/v1` (authoritative)

> **This is the authoritative API specification.** Backend routes, JSON schemas (`/contracts`), and
> frontend TypeScript (`frontend/src/types/`) must all match this document. Contract changes require
> team coordination and a PR touching all of these simultaneously.

JSON Schema files: [`../contracts/`](../contracts/) — see [`../contracts/README.md`](../contracts/README.md)
for the JSON Schema ↔ Pydantic ↔ TypeScript mapping table.

## Conventions

- Prefix: `/api/v1`. Content type: JSON unless stated otherwise (multipart for voice upload).
- **IDs:** `{prefix}-{8 lowercase hex}` (e.g. `TASK-3f9ab2c1`). Fixed prefixes:
  `EMP-` `TASK-` `REM-` `ACT-` `LOG-` `CONV-`.
- **Dates:** `YYYY-MM-DD`. **Timestamps:** ISO 8601 UTC (`2026-11-11T09:30:00Z`).
- **Enums** — task status: `TODO | IN_PROGRESS | BLOCKED | DONE | CANCELLED`;
  priority: `LOW | MEDIUM | HIGH`;
  task/record source: `CHAT | VOICE | MEETING | MANUAL_SHEET | API`;
  action types: `CREATE_TASK | UPDATE_TASK | DELETE_TASK | COMPLETE_TASK | ASSIGN_TASK | CREATE_REMINDER | QUERY`.
- **Error envelope** (all non-2xx):

  ```json
  { "error": { "code": "VALIDATION_ERROR", "message": "The provided task information is invalid", "details": {} } }
  ```

  Codes: `VALIDATION_ERROR` (422), `NOT_FOUND` (404), `CONFLICT` (409, duplicate/state), `UNAUTHORIZED`
  (401), `INTEGRATION_ERROR` (502 Google), `MODEL_ERROR` (503 LLM), `ACTION_NOT_PENDING` (409),
  `INTERNAL_ERROR` (500).

- **Auth:** optional shared bearer token from `API_BEARER_TOKEN` (MVP internal tool, not
  production-grade).

---

## Health

### `GET /api/v1/health`

Summary of backend availability and integration status.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "components": {
    "agent": "ok",
    "google_sheets": "ok | degraded | error | unavailable",
    "model_provider": "ok | error | unavailable",
    "voice": "ok"
  }
}
```

`503` with the error envelope if a mandatory component is unreachable. `model_provider`/`voice` are
advisory here (chat failures surface through `POST /chat`).

---

## Chat

### `POST /api/v1/chat`

Processes a natural-language message and returns the assistant reply plus proposed actions.
**No state is changed by this endpoint.**

Request:

```json
{
  "message": "I need to finish competitor research by Wednesday",
  "employee_id": "EMP-001",
  "conversation_id": "CONV-1a2b3c4d"
}
```

| Field | Required | Rules |
|---|---|---|
| `message` | yes | 1–2000 chars after trim |
| `employee_id` | yes* | must match `EMP-…`; addresses only; *optional only when the sheet defines exactly one employee* |
| `conversation_id` | no | server generates when omitted |

Success — HTTP `200`:

```json
{
  "conversation_id": "CONV-1a2b3c4d",
  "message": "I identified a new research task. Please confirm before I add it.",
  "requires_confirmation": true,
  "proposed_actions": [
    {
      "action_id": "ACT-7c01d9e2",
      "action_type": "CREATE_TASK",
      "payload": {
        "title": "Competitor research",
        "description": "Research competitor products",
        "assignee_id": "EMP-001",
        "due_date": "2026-11-11",
        "priority": "MEDIUM"
      }
    }
  ]
}
```

Non-consequential queries return `"requires_confirmation": false` and may include a filled
`result` (e.g. pending-task list) instead of actions. Failures: `422 VALIDATION_ERROR`,
`503 MODEL_ERROR`.

### `POST /api/v1/actions/{action_id}/confirm`

Validates the pending action again (state may have changed), executes it through the integration
layer, logs activity, schedules follow-ups (e.g. reminders), and creates a `Command_Log` entry.

- `200` → `{ "status": "EXECUTED", "action_id": "ACT-7c01d9e2", "result": { "task": { ...Task } } }`
- Errors: `404 NOT_FOUND`, `409 ACTION_NOT_PENDING` (already executed/rejected — idempotent),
  `422 VALIDATION_ERROR` (re-validation failed), `502 INTEGRATION_ERROR` (Sheets failed; the action
  returns to `PENDING`), `503 MODEL_ERROR`.

### `POST /api/v1/actions/{action_id}/reject`

`200` → `{ "status": "REJECTED", "action_id": "..." }`. Idempotent; `404` for unknown actions.

Action lifecycle: `PENDING → EXECUTED | REJECTED | EXPIRED`. Pending actions expire after 24h
(re-run the chat request).

---

## Tasks

| Endpoint | Description | Success | Errors |
|---|---|---|---|
| `GET /api/v1/tasks` | List; query params: `assignee_id`, `status`, `due_before`, `due_after`, `limit≤200`, `offset` | `200` `{ "tasks": [Task], "total": int }` | 422 |
| `GET /api/v1/tasks/{task_id}` | Fetch one | `200` `{ "task": Task }` | 404 |
| `POST /api/v1/tasks` | **Direct creation** (bypasses the agent; power users/tests). Full validation + duplicate check. | `201` `{ "task": Task }` | 409 CONFLICT, 422 |
| `PATCH /api/v1/tasks/{task_id}` | Partial update (`POST /tasks` body = **create-only fields**: `title`, `assignee_id`, `status`, `priority`, `due_date` required; `description`, `source`, `external_reference` optional). PATCH accepts any optional subset at least one field. | `200` `{ "task": Task }` | 404, 422 |
| `DELETE /api/v1/tasks/{task_id}` | Delete row + `CANCELLED` tombstone log entry. | `204` | 404 |

Task object:

```json
{
  "task_id": "TASK-3f9ab2c1",
  "title": "Competitor research",
  "description": "Research competitor products",
  "assignee_id": "EMP-001",
  "created_by": "EMP-003",
  "status": "TODO",
  "priority": "MEDIUM",
  "due_date": "2026-11-11",
  "created_at": "2026-11-09T07:11:52Z",
  "updated_at": "2026-11-09T07:11:52Z",
  "source": "CHAT",
  "external_reference": null
}
```

Required on create: `title`, `assignee_id` (null allowed only if the caller is archiving → 422),
`status`, `priority`, `due_date` optional (may be `null`). `task_id`, `created_by`, timestamps,
`source` are server-generated. [`../contracts/task.schema.json`](../contracts/task.schema.json).

---

## Employees

| Endpoint | Description | Success | Errors |
|---|---|---|---|
| `GET /api/v1/employees` | List | `200` `{ "employees": [Employee] }` | — |
| `GET /api/v1/employees/{employee_id}` | Fetch one | `200` `{ "employee": Employee }` | 404 |

```json
{ "employee_id": "EMP-001", "name": "Rahul", "email": "rahul@example.com", "role": "Engineer", "created_at": "2026-11-02T09:00:00Z" }
```

(Read routes only in the MVP; employee records are created by editing the sheet's `Employees` tab —
a deliberate design decision, ADR-002.)

---

## Activity

| Endpoint | Description | Success | Errors |
|---|---|---|---|
| `GET /api/v1/activity` | List; `employee_id`, `task_id`, `limit≤200`, `offset` | `200` `{ "activity": [ActivityEntry], "total": int }` | 422 |
| `POST /api/v1/activity` | Log an entry from client (`source: MANUAL_SHEET \| CHAT \| VOICE \| API`). | `201` `{ "activity": ActivityEntry }` | 404 (unknown employee/task), 422 |

```json
{ "activity_id": "LOG-5cd1e01a", "employee_id": "EMP-001", "task_id": "TASK-3f9ab2c1",
  "activity_type": "TASK_COMPLETED", "description": "Marked task completed via chat.",
  "timestamp": "2026-11-09T10:00:00Z", "source": "CHAT" }
```

`activity_type` enum: `TASK_CREATED | TASK_UPDATED | TASK_DELETED | TASK_COMPLETED | REMINDER_SET | REMINDER_SENT | MEETING_EXTRACTED | MANUAL_SHEET_EDIT | NOTE_SUBMITTED`.

---

## Voice

### `POST /api/v1/voice/transcribe`

`multipart/form-data`: `audio` (required; webm/wav/ogg ≤ 10 MB), `language` (optional, default `en`).

```json
{ "transcription": "I completed the authentication module.", "confidence": 0.94, "provider": "web_speech_client" }
```

**MVP honesty note:** the MVP transcription runs in the **browser** (Web Speech API); the frontend
sends the resulting text to `/chat` directly. This endpoint exists so the abstraction is real and a
server-side provider can be plugged in later (ADR recorded first). Until a server-side provider is
implemented it returns `501` with code `NOT_IMPLEMENTED_NOT_WIREABLE`. Errors: `422 INVALID_AUDIO`,
`502` provider errors.

---

## Dashboard

### `GET /api/v1/dashboard/summary`

```json
{
  "team": {
    "total_open": 12, "due_this_week": 4, "overdue": 2, "completed_7d": 9,
    "by_status": { "TODO": 8, "IN_PROGRESS": 3, "BLOCKED": 1 }
  },
  "employees": [
    { "employee_id": "EMP-001", "name": "Rahul", "open_tasks": 4, "overdue": 1, "completed_7d": 3 }
  ]
}
```

---

## Meetings

### `POST /api/v1/meetings/extract`

Accepts **pasted notes or transcript text** only (no automatic Meet integration in the MVP).

```json
{ "title": "Weekly sync", "employee_id": "EMP-001", "text": "...", "date": "2026-11-09" }
```

`200` → `{ "summary": "…", "proposed_actions": [Action…], "requires_confirmation": true,
"decisions": ["…"], "items": ["…"] }`. Extracted actions follow `agent-action.schema.json` and are
confirmed individually through the standard confirm/reject endpoints.

---

## Reminders

| Endpoint | Description | Success | Errors |
|---|---|---|---|
| `GET /api/v1/reminders` | List; query: `task_id`, `employee_id`, `status` | `200` `{ "reminders": [Reminder] }` | 422 |
| `POST /api/v1/reminders` | Create (task_id, employee_id, scheduled_at). | `201` `{ "reminder": Reminder }` | 404 (task/employee), 422 |
| `PATCH /api/v1/reminders/{reminder_id}` | Update `scheduled_at`/`status`. | `200` `{ "reminder": Reminder }` | 404, 422 |

```json
{ "reminder_id": "REM-a1fz9b20", "task_id": "TASK-3f9ab2c1", "employee_id": "EMP-001",
  "scheduled_at": "2026-11-10T09:00:00Z", "status": "SCHEDULED", "created_at": "2026-11-09T10:00:00Z" }
```

`status`: `SCHEDULED | DUE | SENT | CANCELLED`. Only `SCHEDULED → DUE → SENT` and any → `CANCELLED`.
Firing requires the backend process to be running (MVP loop; no push notifications).

---

## Contract consistency checklist (contract changers must re-verify)

- [x] All task fields documented above and in `data-model.md`.
- [x] Date/time formats consistent (UTC ISO 8601; `YYYY-MM-DD` dates).
- [x] ID formats fixed with per-entity prefixes.
- [x] Required/optional fields identified per endpoint.
- [x] Field names match in JSON Schema (`/contracts`), Pydantic (`backend/app/schemas`), TS (`frontend/src/types`) — see `contracts/README.md` mapping.
- [x] One shared action-type enum used everywhere.
- [x] Google Sheets column mapping matches the task schema (`google-sheets-schema.md`).
