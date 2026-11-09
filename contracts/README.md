# Contracts — API JSON Schemas (single field-definition source)

These files are the **shared contract layer** between backend (Pydantic), frontend (TypeScript),
and documentation. Every field that crosses the `/api/v1` boundary is defined in exactly one schema
file below and referenced from `../docs/api-contracts.md` (authoritative), the backend
`backend/app/schemas/`, and `frontend/src/types/`.

**Rule:** any change to entities crosses **all three implementations in a single PR** (plus the docs).
A change only committed in code without updating the schema files will be rejected at review.

| File | Defines | Mirrors (Pydantic — backend/app/schemas/) | Mirrors (TypeScript — frontend/src/types/) |
|---|---|---|---|
| [`task.schema.json`](task.schema.json) | `Task` object + `TaskCreate` / `TaskPatch` constraints | `task.py` | `task.ts` |
| [`agent-action.schema.json`](agent-action.schema.json) | `ProposedAction` (action types, payload unions) | `action.py` | `action.ts` |
| [`chat-request.schema.json`](chat-request.schema.json) | `POST /chat` body | `chat.py` | `chat.ts` (`ChatRequest`) |
| [`chat-response.schema.json`](chat-response.schema.json) | `POST /chat` 200 body (reply + proposed actions) | `chat.py` | `chat.ts` (`ChatResponse`) |

Entities **not** duplicated as JSON Schema (they are documented in `../docs/data-model.md` and implemented
natively on both sides, kept in sync via PR review): `Employee`, `ActivityEntry`, `Reminder`,
`Conversation`, `DashboardSummary` — adding a schema file there is welcomed if they start to drift.

## ID & value conventions (binding across all layers)

- **IDs:** `{prefix}-` + 8 lowercase hex. Prefixes: `EMP-`, `TASK-`, `REM-`, `ACT-`, `LOG-`, `CONV-`.
- **Dates:** `YYYY-MM-DD`. Timestamps: ISO 8601 with `Z` (UTC).
- ** Enums (shared everywhere):**
  - task `status`: `TODO | IN_PROGRESS | BLOCKED | DONE | CANCELLED`
  - priority: `LOW | MEDIUM | HIGH`
  - record source: `CHAT | VOICE | MEETING | MANUAL_SHEET | API`
  - action type: `CREATE_TASK | UPDATE_TASK | DELETE_TASK | COMPLETE_TASK | ASSIGN_TASK | CREATE_REMINDER | QUERY`
  - action status: `PENDING | EXECUTED | REJECTED | EXPIRED`
- **Error envelope (all non-2xx):** `{ "error": { "code": string, "message": string, "details": object } }`
  — codes enumerated in `../docs/api-contracts.md`.

## Sync check

Run `python scripts/validate_contracts.py` (also in CI). It verifies every file is valid
Draft 2020-12 JSON Schema. Cross-layer drift is caught by `tests/contract/test_api_shapes.py`
(backend renders each schema's example payload and compares to fixtures) and by the frontend
`services/` compile-time types — together the three representations stay in lock-step.
