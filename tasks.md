# Task Board — Milestones, Owners, Acceptance Criteria

> **Live board.** Update the `Status` cell (not the descriptions) as work progresses. Statuses: `TODO`
> `IN_PROGRESS` `BLOCKED` `REVIEW` `DONE`. Priorities: `P0` (blocks prototype) `P1` `P2`.
> One owner per implementation file. Task IDs are stable — reference them in commits and PRs.

---

## 1. Module ownership map (enforced in PR review)

| Files | Owner |
|---|---|
| `backend/**` | **A** |
| `agent/**` | **A** |
| `integrations/google_sheets/**` | **B** |
| `frontend/**` | **C** |
| `voice/**` | **C** |
| `contracts/**`, root + `docs/**`, `.env.example`, CI | **A** (shared owner; changes need all-team ack) |
| `tests/**` | **A** (contract tests) with module-specific tests contributed by each owner inside their PRs |

Rule: nobody edits another owner's files without that owner's review, and contract changes are
proposed **before** implementation (CONTRIBUTING.md rule 6).

---

## Milestone 0 — Repository Foundation ✅ (current)

Team reviews `AGENTS.md`, `skills.md`, `docs/architecture.md`, `docs/api-contracts.md`, `tasks.md`
before any feature code. Sign-off = each DE comments on the foundation PR.

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-001 | Read AGENTS.md + skills index + architecture + API contracts + this board; raise conflicts as PR comments | A, B, C | P0 | — | Each DE has reviewed the 5 files; all questions answered in the foundation PR thread | TODO |
| T-002 | Sign-off: merge foundation to `develop` | A | P0 | T-001 | CI green; contracts validated; `develop` exists with the merged PR | TODO |

---

## Milestone 1 — Independent Module Setup (parallel, no cross-module wiring)

### Developer A — backend & agent scaffolding

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-010 | Backend skeleton: `backend/app/main.py` (FastAPI app, `/api/v1/health`), `core/config.py` (pydantic-settings reading `.env`), CORS from `CORS_ORIGINS`, error-envelope exception handlers | A | P0 | T-002 | `uvicorn app.main:app` serves; `GET /health` returns component map per api-contracts.md; `pytest tests/unit` passes with 1 config test | REVIEW |
| T-011 | Pydantic schemas mirroring `contracts/*.schema.json` (`models/`, `schemas/`) | A | P0 | T-010 | Pydantic classes match the mapping table in `contracts/README.md`; contract tests validate schema examples round-trip | REVIEW |
| T-012 | **Ports** (interfaces): `services/ports.py` with `TaskRepository` `EmployeeRepository` `ActivityLogRepository` `ReminderRepository` protocols + in-memory fakes for tests | A | P0 | T-010 | Protocol docs match data-model.md; fakes used by route unit tests without any Sheets import | REVIEW |
| T-013 | Agent scaffolding: `agent/app/state.py`, `graph.py` with node registry + pass-through wiring of all nodes, working `UNKNOWN`-intent fallback reply | A | P0 | T-002 | Graph executes with a mocked provider; clarification reply path proven by unit test | REVIEW |
| T-014 | Model-provider abstraction: `agent/app/models/` `BaseModelProvider` + `OllamaProvider` (httpx) + `MockModelProvider`; env-driven selection | A | P0 | T-013 | Swapping `MODEL_PROVIDER` changes implementation without code edits; timeout/retry unit tests with a fake transport | REVIEW |
| T-015 | Action store: in-memory pending-action registry (create/get, 24h expiry) used by confirm/reject | A | P0 | T-011 | Expiry + idempotency unit tests | REVIEW |

### Developer B — Google Sheets integration scaffolding

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-020 | Auth setup: service-account creation guide + `google_sheets/client.py` (`google-api-python-client`), retry on 429/5xx, quota-friendly batching | B | P0 | T-002 | Doc in module `AGENTS.md`; client unit-tested against a fake transport; no credentials needed for unit tests | REVIEW |
| T-021 | Sheet setup script + docs: tab creation for the 5 tabs with exact headers of `docs/google-sheets-schema.md`, welcome 3 test employees | B | P0 | T-020 | A dev can run setup in < 10 min on a private sheet; headers match doc byte-for-byte | REVIEW |
| T-022 | `mapper.py`: row ↔ domain objects (all 5 tabs), per google-sheets-schema.md §2 rules | B | P0 | T-020 | Round-trip unit tests; empty-cell→null & unparseable-cell→degraded behavior covered | REVIEW |
| T-023 | `repository.py`: implement the 4 ports of T-012 via client+mapper; stable-ID CRUD; never trust row numbers | B | P0 | T-021, T-022, T-012 | Repository passes port-conformance tests using `FakeGoogleSheetsClient` (also contributed to `tests/unit/`) | REVIEW |
| T-030 | **(B contributes) `FakeGoogleSheetsClient`** in `tests/unit/`: in-memory client with simulated manual-edit hooks | B | P0 | T-020 | A's route tests + B's repo tests reuse this one fake; it's the single fake (testing-strategy.md) | REVIEW |

### Developer C — frontend & voice scaffolding

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-040 | Frontend scaffold: Vite+React+TS, Tailwind, Axios instance (`VITE_API_BASE_URL`), React Query + Zustand providers, router-less layout | C | P0 | T-002 | `npm run dev` starts; `tsc --noEmit` clean; lint clean | REVIEW |
| T-041 | API schemas in TS mirroring contracts: `src/types/` + `services/apiClient.ts` | C | P0 | T-011 (schemas to mirror) | Interfaces deliver the mapping in `contracts/README.md`; build passes | REVIEW |
| T-042 | App shell: sidebar nav (Chat, Tasks, Dashboard), employee-id selector (state), basic empty pages | C | P1 | T-040 | Navigation works; employee_id persists in Zustand | REVIEW |
| T-043 | Voice module skeleton: `voice/schemas.py` DTOs + `Transcriber` protocol + `WebSpeechConfigDTO` (client-side guidance) and a stub provider | C | P1 | T-011 | Unit tests for DTO validation | REVIEW |

---

## Milestone 2 — Core Functional Implementation

### Developer A

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-050 | LLM nodes: `classify_intent` + `extract_entities` prompts & fixtures (structured JSON), heuristic post-fixups | A | P0 | T-013, T-014 | Extraction unit tests cover ≥ 10 sentences incl. "Wednesday", assignee-to-me, "completed..."; invalid JSON → retry → clarification, never fabricated write | REVIEW |
| T-051 | Deterministic nodes: `resolve_employees`, `resolve_dates`, `validate_and_propose` (+ duplicate check behind the port) | A | P0 | T-050, T-012 | "Me"→caller; ambiguous names → clarification listing options; duplicate (title+assignee+open) blocked with a message | REVIEW |
| T-052 | Confirmation endpoints: `POST /actions/{id}/confirm` + `/reject` — re-validate & execute through awarded ports; Command_Log entries; error envelope | A | P0 | T-015, T-012 | Unit+contract tests: PENDING→EXECUTED (task row created via fake repo), rejection, idempotent, expired, re-validation failure leaves PENDING | REVIEW |
| T-053 | Remaining base task/employee/activity/reminders/voice/dashboard routes from api-contracts.md | A | P0 | T-012 | Contract tests: every documented route → documented status codes & shapes (mocked ports) | REVIEW |

### Developer B

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-060 | Activity logging: `Activity_Log` repository usage + internal helper to append entries from every repo mutation | B | P0 | T-023 | Every create/update/delete via repos produces an Activity_Log row in the fake-client tests | REVIEW |
| T-061 | Reminders repository (`Reminders` tab) incl. status transitions schedule→due→sent→cancel | B | P0 | T-023 | Unit tests per data-model status rules | REVIEW |
| T-062 | Command log writing: `Command_Log` rows (conversations), written by repo interface A calls | B | P0 | T-023 | Fake-client tests verify rows for propose/execute/reject flows | REVIEW |
| T-063 | Integration test sheet + opt-in tests (`tests/integration/`): real spreadsheet CRUD smoke | B | P1 | T-021, T-023 | Passing locally with `GOOGLE_SHEET_TESTS_ENABLED=1` and a throwaway sheet; skipped otherwise | REVIEW |

### Developer C

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-070 | Chat UI: message list, input box, React Query mutation → `/chat`, optimistic/typing states, conversation_id handling | C | P0 | T-040, T-041, T-053 (route contract) | Manual happy path with mocked API fixtures; error/loading states render | REVIEW |
| T-071 | Confirmation UI: proposed-action cards showing extracted fields; Confirm/Reject buttons wired to the two endpoints | C | P0 | T-070, T-052 | Confirm/reject updates the card + chat log; failure toasts use the error envelope | REVIEW |
| T-072 | Task list + details view: filters (assignee, status), sort by due date, complete button → PATCH | C | P0 | T-040, T-041 | Renders fake fixture data; component tests on render states | REVIEW |

---

## Milestone 3 — Cross-Module Integration (A leads; B/C points of contact)

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-080 | Wire the chain in `backend`: route → agent graph → `validate_and_propose` → action store → confirm endpoint → **real** Sheets repositories behind ports (B's modules) | A | P0 | T-052, T-023 | Contract test `test_full_flow.py` — mocked LLM + **real repo code + fake client**: propose → confirm → Tasks/Activity/Command rows | REVIEW |
| T-081 | Dashboard summary endpoint: statistics with real repository queries | A | P1 | T-053, T-023 | Numbers match fixture sheet in tests | REVIEW |
| T-082 | Error/timeout hardening: integration failure → 502 + action stays PENDING; LLM timeout → retry → 503 | A | P1 | T-080 | Unit tests for both paths with forced failures | TODO |
| T-090 | Frontend ↔ backend live wiring: replace fixtures with real endpoints, base-URL config, request/error interceptors — **D-OWNER: C** (A reviews contract compliance) | C | P0 | T-070/71/72, T-053 | Demo via local dev servers; coordinator passes CI type checks | REVIEW |
| T-091 | Dashboard page (team + per-employee cards using `/dashboard/summary`) | C | P1 | T-090, T-081 | Renders live data consistent with the test sheet | REVIEW |

---

## Milestone 4 — Advanced MVP Features

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-100 | Manual-edit reconciliation: `reconciliation.py` poll loop (~`RECONCILIATION_POLL_SECONDS`), rules per google-sheets-schema.md §3, `MANUAL_SHEET_EDIT` logging, self-write guard | B | P1 | T-023, T-080 | Fake-client tests: manual cell edit detected ≤ 1 poll; app's own writes ignored; conflict rule honored | REVIEW |
| T-101 | Reminder scheduler loop: background asyncio task executing reminders (schedule→due→sent) + logging, **runs only while the server process runs** (documented) | A | P1 | T-061, T-080 | Unit tests with fake clock; reminders requested via chat → CREATE_REMINDER → executed row | REVIEW |
| T-102 | Meeting extraction workflow + `POST /meetings/extract` (P2 in requirements; start in M4 only if P1 exit criteria are green) | A | P2 | T-080 | Fixture-based extraction tests; individual confirmation of extracted actions | REVIEW |
| T-110 | Voice input UI: mic button + Web Speech API capture → text; fallback message on unsupported browsers | C | P1 | T-070 | Works in Chrome; graceful degradation; transcription rendered in the chat input (editable) | REVIEW |
| T-120 | Voice route implementation: wire `voice.Transcriber` into `POST /voice/transcribe` (501 → real provider when design allows) | A+C (A owns route; C the module) | P1 | T-043 | Contract test documents the MVP 501 mode per api-contracts.md; DTO validation unit tests | REVIEW |

---

## Milestone 5 — Testing & Prototype Demonstration

| ID | Task | Owner | P | Depends | Acceptance criteria | Status |
|---|---|---|---|---|---|---|
| T-130 | End-to-end demo script (docs/testing-strategy.md § demonstration): live run + record issues | A | P0 | T-090, T-081, T-100, T-101 | Full 7-step scenario passes live; blockers opened as issues | TODO |
| T-140 | Integration-test credentials run + reconciliation validation on a real sheet | B | P0 | T-063, T-100 | Real-sheet results match fake-client test conclusions | REVIEW |
| T-150 | UX polish + demo machine setup (fresh-clone startup, dry run of the README) | C | P1 | T-130 | A new machine passes README → demo in ≤ 30 min of setup | TODO |

---

## Status legend & update rules

- Update **only** `Status` here + link the PR in the PR template's "Task reference" field.
- `BLOCKED` requires a comment on the dependency task naming the blocker.
- Moving to `DONE` = merged to `develop` (CI green) — not merely "implemented".
- B may not change repo interfaces (T-012) or employee/task semantics without a coordinated PR
  (rule 10 in CONTRIBUORING.md), and vice versa for A writing data expectations into B's files.
