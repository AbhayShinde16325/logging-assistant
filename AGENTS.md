# AGENTS.md — Instructions for AI Coding Agents

> **This file is the primary instruction manual for every AI coding agent working in this repository.**
> Read it fully before modifying any file. Module-level `AGENTS.md` files (in `frontend/`, `backend/`,
> `agent/`, `integrations/`, `voice/`) refine — but never contradict — this document.

---

## 1. Project context

**Project:** Personal AI Project Management Agent (repository: `logging-assistant`).
An AI-powered assistant that a 3-person team uses as a shared work coordinator: it accepts text and
voice instructions, understands work-related activities, manages tasks, tracks employee activity,
and sends proactive reminders.

**MVP scope (do not exceed it):**

```text
User Input → AI Understanding → Structured Action → User Confirmation
→ Google Sheets Update → Activity Tracking → Reminder
```

- Text chat (P0) and voice input (P1).
- Natural-language task extraction, assignment, modification, completion.
- Google Sheets as the **only** shared data store for the MVP.
- Detection and reconciliation of manual edits in the spreadsheet.
- Activity logging, reminders, meeting action-item extraction, basic dashboard.
- ~3 employees now, ~10 later. **This is a prototype, not an enterprise platform.**

**Technology stack (fixed unless an ADR is written first):**

| Layer     | Tech                                                                 |
|-----------|----------------------------------------------------------------------|
| Frontend  | React, Vite, TypeScript, Tailwind CSS, Axios, React Query, Zustand   |
| Backend   | Python, FastAPI, Pydantic v2, Uvicorn                                |
| AI/Agent  | LangGraph orchestration, Ollama (local), configurable model provider  |
| Integration | Google Sheets API (service account), optional Google Apps Script    |
| Voice     | Browser-based capture (Web Speech API MVP), pluggable transcription  |
| Storage   | Google Sheets only. No PostgreSQL/Redis/Kafka in the MVP.             |

**Architecture in one paragraph:** The React frontend talks only to the FastAPI backend. The backend
owns every API route, validates everything, and calls three things: (1) the **agent module** (LangGraph
graph that uses the LLM to classify intents and extract structured actions — it never writes to Sheets),
(2) the **integration layer** (Google Sheets repositories behind a service-account client), and
(3) the **voice module** (transcription abstraction). See `docs/architecture.md`.

**Authoritative documents (read before implementing anything):**

| Purpose | File |
|---|---|
| Module boundaries & dependency rules | `docs/architecture.md` |
| API endpoints, payloads, errors | `docs/api-contracts.md` (authoritative) |
| Entities & validation rules | `docs/data-model.md` |
| Spreadsheet tabs & column mapping | `docs/google-sheets-schema.md` |
| Agent graph, nodes, state | `docs/agent-workflow.md` |
| Task IDs, owners, acceptance criteria | `tasks.md` |
| Skill-specific instructions | `skills.md` + relevant `skills/*/SKILL.md` |

---

## 2. Mandatory development rules

1. Read this root `AGENTS.md` before modifying anything.
2. Read the relevant skill file (`skills/*/<name>/SKILL.md`) before implementing a feature.
3. Read the relevant architecture and API documentation listed in the table above.
4. Never independently change the agreed architecture. If something must change, write an ADR in
   `docs/decisions/` and get team agreement in the PR first.
5. Never modify API contracts (`docs/api-contracts.md`, `contracts/*`) without notifying the team and
   updating: JSON schemas in `/contracts`, backend Pydantic schemas, and frontend TypeScript types **together**.
6. Never introduce a new dependency without documenting its purpose in the PR description.
7. Never create duplicate implementations of existing services (one task repository, one error
   formatter, one date utility — check `services/` and `utils/` first).
8. Never hardcode API keys, passwords, credentials, tokens, or secrets.
9. Use `.env.example` to document every environment variable you introduce.
10. Never commit actual `.env` files or Google service-account credentials (`.gitignore` covers this;
    keep credentials outside the repo entirely).
11. Add tests for new business logic (see `skills/testing-and-integration/SKILL.md`).
12. Keep functions modular and maintainable (single responsibility; small, named functions).
13. Use type hints in Python (mypy-friendly Pydantic v2 style).
14. Use TypeScript types instead of `any` wherever practical.
15. Follow existing naming conventions (`snake_case` Python, `camelCase` TS, `PascalCase` components).
16. Do not modify files owned by another developer without coordination (ownership map is in `tasks.md`
    §1 and each module's `AGENTS.md`).
17. Do not silently change another developer's implementation — raise it in the PR or on the team channel.
18. Update documentation whenever architecture or behavior changes.
19. If an AI agent encounters an instruction conflict, the safest reading wins: stop, make the smallest
    reversible change, and flag the conflict in the PR description.
20. Do not invent capabilities of external APIs (Google Sheets, Web Speech, Ollama). Verify against the
    linked official docs named in the relevant SKILL.md.

---

## 3. API rules

- The backend owns the API implementation. The frontend calls `/api/v1/*` only.
- `docs/api-contracts.md` is **authoritative**. If code and contract disagree, one of them is wrong —
  fix both in the same PR, never leave them diverged.
- Shared schemas in `/contracts/*.schema.json` must stay synchronized with backend Pydantic schemas
  and frontend TypeScript interfaces (mapping table: `contracts/README.md`).
- Return the consistent error envelope on every failure:

  ```json
  { "error": { "code": "SOME_ERROR_CODE", "message": "Human-readable message", "details": {} } }
  ```

- Use Pydantic validation at route boundaries; never accept raw dicts into services.
- Never allow an LLM-generated action to bypass application-level validation.

---

## 4. AI agent rules (LangGraph / LLM)

- The LLM **interprets** instructions; it does **not** write to Google Sheets, decide authorizations,
  or generate IDs that the system trusts.
- The agent produces **structured actions** (`contracts/agent-action.schema.json`). Model output is
  parsed with Pydantic and never assumed to be valid JSON.
- The backend validates every proposed action: field types, employee IDs, task IDs, enumerations.
- Destructive or consequential actions (create/update/delete/assign) require **user confirmation**
  through the confirm/reject endpoints before execution.
- Only approved actions reach integration services.
- Maintain a clear separation: LLM reasoning (`agent/`) ≠ application logic (`backend/app/services/`)
  ≠ external integrations (`integrations/`).
- Do not trust model-generated employee IDs, task IDs, or authorization decisions without validation.
- The model provider must be swappable (`agent/app/models/` abstraction); business logic never imports
  Ollama or any specific SDK directly.

---

## 5. Git rules

Branch model:

```text
main            ← protected, stable; never pushed to directly
develop         ← integration branch (default for PRs)
feature/<developer>/<feature-name>
fix/<developer>/<issue-name>
```

- Never push directly to `main` (branch protection).
- Never push directly to `develop` either — open a pull request even for small changes.
- Keep commits focused: one logical change per commit, imperative message ("Add task schema"), no
  artifacts.
- Pull or rebase from `develop` before integrating (`git fetch origin && git rebase origin/develop`).
- Resolve conflicts with the responsible module owner, not unilaterally.
- Require tests to pass (locally and in CI) before merging.
- Squash-merge feature PRs into `develop` (see `docs/development-workflow.md`).

**Module ownership (enforced via review):** backend+agent — Developer A; Google Sheets integration —
Developer B; frontend+voice(+UI orchestration) — Developer C. Full map with file lists: `tasks.md` §1.
Shared files (`contracts/`, `docs/api-contracts.md`, `.env.example`, root docs) have a single owner too:
Developer A, with mandatory coordination for changes.

---

## 6. Definition of done

A task is complete only when **all** of these hold:

- [ ] Implementation complete per `tasks.md` acceptance criteria.
- [ ] Relevant tests pass locally and in CI (backend `pytest`, frontend lint/typecheck/tests).
- [ ] API contracts respected; schemas synchronized across JSON Schema / Pydantic / TypeScript.
- [ ] Documentation updated where the architecture or behavior changed.
- [ ] No secrets committed; new env vars documented in `.env.example`.
- [ ] Changes committed to a feature branch, up to date with `develop`.
- [ ] Pull request open with: modules affected, how tested, test results, dependency list (if new deps).
- [ ] Status column in `tasks.md` updated (`TODO → IN_PROGRESS → REVIEW → DONE`).
