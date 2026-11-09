# Testing Strategy

Goal: fast, reliable tests that run in CI **without** external credentials, plus clearly separated
opt-in integration tests that explicitly need a real test spreadsheet.

## Test pyramid (repo layout)

```text
tests/
├── unit/           fast, no external services, all fakes (pytest default run)
├── contract/       API + schema shape validation (FastAPI TestClient + jsonschema checks)
├── integration/    REAL Google Sheets + REAL Ollama — opt-in, marked `integration`
tests/requirements.txt   pytest, pytest-asyncio, httpx, ruff, mypy (dev-only deps)
```

Unit/contract runs are triggered by `pytest` at repo root. Integration tests are skipped unless
`GOOGLE_SHEET_TESTS_ENABLED=1` **and** real credentials/bindings are configured (see env matrix) —
so CI contributors never need credentials. Note: pytest collects from the repository root; keep
fixtures importable (`tests/*/__init__.py`) so pytest doesn't double-import modules.

## What each layer covers (mapped to the required test categories)

| Category | Where | How mocked / verified | Priority |
|---|---|---|---|
| Task extraction (NL → structured action) | `tests/unit/agent/test_extraction*.py` | Fake `BaseModelProvider` returning recorded fixture responses (tiny known-good model messages) — **not** network calls | P0 |
| Date/phrase extraction & resolution | `tests/unit/agent/test_date_resolution.py` | Deterministic node tests: "Wednesday", "tomorrow", "two hours before deadline", "next Friday", ambiguous → clarification | P0 |
| Employee identification & resolution | `tests/unit/agent/test_employee_resolution.py` | `FakeEmployeeRepository` with 3 fixture employees; "me"→EMP-00x assignment; ambiguous name → clarification; unknown name → clarification | P0 |
| Invalid task data handling | `tests/unit/agent/` + `tests/contract/test_*_schemas.py` | Pydantic/schema validation: bad enum, missing title, oversized title, wrong date format, FK-not-known assignee | P0 |
| Duplicate task detection | `tests/unit/services/test_task_service.py` | `FakeTaskRepository` with a pre-existing open task; candidate create → duplicate flag → assistant asks instead of silently continuing | P0 |
| Confirmation & rejection | `tests/unit/services/test_action_lifecycle.py`, `contract/` | PENDING→EXECUTED on confirm; PENDING→REJECTED on reject; idempotency; EXPIRED after 24h clock injection; confirm with expired task → VALIDATION_ERROR + action stays pending | P0 |
| Google Sheets CRUD (against the real repo layer) | `unit/integration_wrappers/` | `FakeGoogleSheetsClient` (in-memory tab dict) drives the repo/mapper/reconciliation code: create→read→update→delete→list of Tasks/Employees/Activity/Reminders | P0 |
| **Real** Google Sheets integration | `tests/integration/test_sheets_end_to_end.py` | Opt-in, marked `@pytest.mark.integration`; needs a **throwaway test spreadsheet**, its ID and a service account JSON from `.env`-side values; verifies the mapper/repo/heuristic against the real API | P1 |
| Manual spreadsheet edits & reconciliation | `unit/integration_wrappers/test_reconciliation.py` | Fake client simulating direct row edits/clears/deletions → poll detects → Activity_Log entries, conflicts resolved per google-sheets-schema.md §3 | P0 |
| API response validation | `tests/contract/test_api_shapes.py` | TestClient over the app with mocked ports — every documented route, error envelope code, and 201/404/409/422/502/503 statuses per docs/api-contracts.md | P0 |
| Frontend ↔ API integration | `frontend/src/**` | Vitest/React Query component tests; Axios calls mocked via MSW/`fetch`-level fake hitting the same JSON fixtures that back frontend type definitions (contract ↔ frontend consistency check — run the same `contracts/*.schema.json` against samples) | P1 |
| Voice transcription handling | `tests/unit/voice/` | Audio DTO validation, provider-error mapping; browser-side Web Speech can't be unit-tested — covered in the demo script | P1 |
| Reminder scheduling | `tests/unit/services/test_reminder_scheduler.py` | Fake clock + fake repo; scheduled→due→sent transitions; cancel; fire-as-server-loop semantics (no push) | P1 |
| End-to-end (mocked externals) | `tests/contract/test_full_flow.py` | simulate full `/chat` → propose → `/confirm` → repo rows created → activity written; a run of the same happy path via `/reject`; the demo-scenario dialog below, but wired and asserted |
| Multi-turn client integration | `tests/contract/test_chat_flow.py` | `/chat` twice: second turn references the entity from the first via client-held conversation_id | P1 |

## Mock/fake inventory (single source, reused everywhere)

- `MockModelProvider` — canned structured JSON per intent; covers API-shape drift from prompt edits.
- `FakeGoogleSheetsClient` — in-memory sheet; simple O(1) get/set/clear; supports simulated manual edits + cache.
- `FakeTaskRepository` / `FakeEmployeeRepository` / `FakeActivityLogRepository` / `FakeReminderScheduler` — port-level fakes (see `skills/testing-and-integration/SKILL.md`).

Rule: **unit tests never make network calls**; only `tests/integration/*` do, guarded by the env flag
and cleaned up against a disposable sheet (`TEST_*`).

## Risk-mitigation: regenerate test fixtures whenever prompts change

Agent-extraction tests are the danger zone: prompt edits can silently change output shapes. Each
fixture pair (prompt version ↔ expected structured output) lives next to the test; CI runs those
every push (cheap, no LLM). REAL-LLM spot checks live in `/tests/integration/test_ollama_smoke.py`
(tagged `integration`, opt-in, 1 smoke message).

## Complete end-to-end demonstration (manual, Milestone 5)

```text
1. (Lead) "Assign competitor research to me by Wednesday."
   → assistant proposes CREATE_TASK (title, due, assignee=you), needs confirmation.
2. User: confirms → sheet gains a Tasks row, Activity_Log row, Command_Log row.
3. Employee: "What are my pending tasks?" → does NOT require confirmation; lists 1 task.
4. Employee: "Done with competitor research." → COMPLETE_TASK proposal, confirm → status DONE.
5. Manual edit: change the row's title / status directly in the sheet;
   within ≤60s the reconciliation loop reports change & logs MANUAL_SHEET_EDIT.
6. (Lead) "Summarize what everyone worked on this week." → activity summary, no confirmation.
7. "Remind me one day before each open task deadline." → CREATE_REMINDER proposals, confirm.
```

## Definition of testing done (per task with code)

- unit + contract tests for the change, all green locally and in CI
- touched schemas re-validated (`scripts/validate_contracts.py`)
- no new flaky tests (retry ≤1 once inline if genuinely deterministic, else fix the test greedily)
