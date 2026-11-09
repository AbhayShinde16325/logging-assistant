# SKILL: Google Sheets Integration

> **DE (skill-steward):** Developer B · Applies to: `integrations/**` and repository tests.

## 1. Skill purpose

Implement robust task data operations over Google Sheets: service-account authentication, tab
mappings (row ↔ domain object), CRUD through the repository ports, duplicate avoidance, and
detection/reconciliation of manual edits.

## 2. When the agent should use this skill

Any task touching `integrations/google_sheets/**`, the sheet creation/setup, or reconciliation.

## 3. Relevant directories and files

- Code: `integrations/google_sheets/` (`client.py`, `mapper.py`, `repository.py`, `reconciliation.py`)
- Spec: `../docs/google-sheets-schema.md` (**authoritative**), `../docs/data-model.md`,
  decision: `../docs/decisions/ADR-002-google-sheets-as-data-store.md`
- Ports: implemented interfaces are proposed by A in `backend/app/services/ports.py` — coordinate
  before changing any signature (`tasks.md` rule).
- Tests: `../tests/unit/` via `FakeGoogleSheetsClient` (T-030) and `../tests/integration/` (opt-in).
- Reference docs (verify behavior, never guess): Google Sheets API v4 docs
  <https://developers.google.com/sheets/api> and google-auth service-account guide.

## 4. Technology-specific implementation rules

- **Auth**: service-account JSON via `GOOGLE_APPLICATION_CREDENTIALS` (path or inline setting —
  never the file itself); scopes: `https://www.googleapis.com/auth/spreadsheets`; the frontend never
  sees credentials.
- **Client** (`client.py`) exposes only the granular reads/writes needed (`get_rows`, `append_row`,
  `update_row`, `clear_row/clear_range`, `get_header`); wraps 401/403/429/5xx in typed errors with
  backoff-and-retry for 429/503 (Sheets quota rule); no business logic, no caching of identities.
- **Mapper** (`mapper.py`): exact header order per `google-sheets-schema.md` §1; empty cell → `null`
  (optional fields) or typed validation error (required field); dates `YYYY-MM-DD`, timestamps UTC
  ISO 8601; unknown extra columns ignored; enum values validated on read, invalid ones fetched into
  an error row marker — never silently coerced.
- **Repository** (`repository.py`) implements the ports:
  - Find rows by ID lookups (`task_id` exact match) — **never** by row order or number; IDs
    generated at write time (`uuid4().hex[:8]`) with configurable reserved-none piece for tests.
  - Create, fetch (also detail), list (supports the `/api/v1/tasks` filters), update partial
    fields, delete (rows **physically** removed; activity tombstone entry added).
  - **Duplicate prevention** (FR-16): check for existing (assignee_id, lowercase title equal, status
    in `TODO,IN_PROGRESS,BLOCKED`) before creating; raise duplicate error surfaced as user-facing
    proposition question; catch also list on create race (last-write validator).
- **Reconciliation** (`reconciliation.py`) per google-sheets-schema.md §3:
  - Poll `RECONCILIATION_POLL_SECONDS` (default 60) inside a background asyncio loop owned by the
    backend (module provides the callable, not the loop lifecycle).
  - Compare snapshots; treat content drift with unchanged/stale `updated_at` as manual edit; skip
    rows whose `updated_at` is inside the guard window (app writes).
  - On detection: write `MANUAL_SHEET_EDIT` activity rows, then let the backend surface the change
    in chat/dashboard views. Conflicts: manual edit wins; the pending app action is re-validated and
    may become a clarification (never silently overwritten behavior).
  - Detect missing rows (row manually deleted) as "unknown missing rows" to answer queries with
    'removed manually' rather than fabricated data.
- **Self-race guard**: snapshot written immediately after own write and bookmarked; never re-mark
  own writes.

## 5. Coding conventions

Repository methods read like domain sentences (`get_task`, `list_tasks`, `add_task`); typing with
dataclass/pydantic converted from mapper; one typed exception per failure class for easy route mapping.

## 6. Dependencies and interfaces

- Implementation side libs: `google-api-python-client`, `google-auth` (pin versions in
  `backend/requirements.txt`).
- Providing new repo operations must go through the Port-Def PR — A owns ports; B implements.
- No behavior beyond documented needs (do not invent custom formulas, Apps-Script triggers).

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Using row numbers as IDs | Stable `TASK-…`/`EMP-…` used in column A |
| Assuming connected-first header row is fixed | Verify headers parity against the schema doc; fail fast on mismatch |
| Trusting sheet **types** | Parse and validate everything; typed empty/invalid flags |
| Double-write on reconciliation | Snapshot-cache after app writes; guard window |
| Hiding Google API failures with broad `except` | Typed exceptions → error envelope (`502 INTEGRATION_ERROR`) |
| Exposing creds to tests/logs/frontend | Env paths only; scrub tracebacks; no JSON paste in PRs |

## 8. Testing requirements

- Unit tests with `FakeGoogleSheetsClient` (in-memory): implement all CRUD, header guard,
  mapper round-trip, dup check, missing-row behavior, self-write guard, manual-edit detection.
- Contract tests: routes with mocked repositories verify the envelope.
- Opt-in integration tests (real sheet): marked; require a disposable test spreadsheet + service
  account; skipped by default, run before the final demo (T-140).

## 9. Completion checklist

- [ ] Tab/mapping changes synchronized with `docs/google-sheets-schema.md` and ADR-002
- [ ] Ports untouched (or coordinated with A in the same PR)
- [ ] Fake-client unit green; `pytest -q` at root green; integration tests prepared/marked
- [ ] Activity/Command logging verified for every mutation path
- [ ] No credentials/secrets in code, logs, fixtures, or PR contents
