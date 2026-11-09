# SKILL: FastAPI Development

> **DE (skill-steward):** Developer A · Applies to: backend & shared-contract contributors.

## 1. Skill purpose

Implement the `/api/v1` API: route handlers, Pydantic schemas, service layer, validation, the
consistent error envelope, and their tests.

## 2. When the agent should use this skill

Any task touching `backend/**` (routes, schemas, services, error handling, DI).

## 3. Relevant directories and files

- Code: `backend/app/` (`api/routes/`, `schemas/`, `services/`, `api/dependencies.py`, `core/`, `utils/`)
- Contracts: `../contracts/*.schema.json` (authoritative), `../docs/api-contracts.md`
- Tests: `../tests/unit/`, `../tests/contract/`
- Config: `../.env.example` ↔ `backend/app/core/config.py` (two-way discipline)
- Root `AGENTS.md` §3 (API rules) and `backend/AGENTS.md`

## 4. Technology-specific implementation rules

- **Routes** stay thin (parse → service call → respond). No business logic or repository access in
  route bodies; dependencies provide adapters (server wiring stays in one file).
- **Pydantic v2 everywhere**: request/response models are Pydantic classes that mirror
  `contracts/` 1:1 (`model_dump(mode="json")` for bodies; converters in schemas, not scattered).
- **Error envelope**: implement `{ "error": { "code", "message", "details" } }` with centralized
  exception handlers in `app/main.py`; error codes live in one enum module. No route creates raw
  `HTTPException` dicts — use helpers in `app/utils/` so all responses look identical.
- **Status codes** per `docs/api-contracts.md`: 200 read/confirm, 201 create, 204 delete, 404/409/
  422/501/502/503 per concrete route table. `VALIDATION_ERROR` on body parse failure — never leak naked 500s.
- **Validation layering**: schema-level (types, enums, formats) at the route; entity-level (FK
  exists, duplicates) in services via repository ports; **context-level** (action confirm re-check)
  only in the confirm flow.
- **Never** accept an LLM-generated action struct as a request body — confirm/reject take an
  `action_id` and look up the already-validated pending action (`action_service`), preventing
  contract bypass via client tampering.
- **Deps/DI**: concrete adapters only in `api/dependencies.py`; services receive ports; settings via
  `config.py` (`pydantic-settings`); no `import os` sprinkles.
- **Background work** (reminder scheduler, sheets poller) = asyncio tasks started on app startup
  with graceful shutdown; never threads appended ad-hoc (uvicorn multiprocess safety).

## 5. Coding conventions

- snake_case modules/functions; services/class per resource; `Fake*` fakes; full type hints; Pydantic
  v2 `Field` constraints; docstrings on every public service method; no `print()` (use stdlib
  `logging` with `LOG_LEVEL`).

## 6. Dependencies and interfaces

- Added deps require justification in the PR (stack discipline in root AGENTS.md).
- Endpoints communication contract changes must also update TypeScript types — coordinate with
  Developer C (rule: shared-file owner review, A's PR merges last).
- Agent boundary: services consume the agent via one callable (run message → ChatResponse-request
  object output); the backend owns **no** prompt knowledge.

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Executing proposed actions inline during `/chat` | `/chat` never mutates state; execution lives only in confirm |
| Hand-rolled JSON responses | Typed response models; consistent envelope |
| Route catches everything → 500 holes | Map expected failures via services' typed exceptions to envelope codes |
| FK checks against "trusted" LLM IDs / client IDs | Re-verify IDs against repository state in the operation service |
| New env var only in config.py | Add to `.env.example` and document in module AGENTS |

## 8. Testing requirements

- **Unit tests** per service: Fake ports (ownership of fake fixtures in `tests/unit/`).
- **Contract tests**: TestClient over the app with mocked ports — every documented endpoint, status
  code, and envelope; plus jsonschema-sample round-trips per `contracts/`.
- Rule of thumb: every documented route in `docs/api-contracts.md` has ≥ 1 happy-path + ≥ 1 error-path
  contract test; failure of that mapping fails CI.
- Never require Ollama/Sheets in unit/contract suites (mocked transports / in-memory fakes).

## 9. Completion checklist

- [ ] Route + Pydantic schema added **with** the contract update (if any) in the same PR
- [ ] Error paths create envelope responses with documented codes
- [ ] `pytest -q` unit + contract green locally & in CI
- [ ] `docs/api-contracts.md` + `contracts/` in sync (schema validator script passes)
- [ ] New env vars in `config.py` + `.env.example`; no secrets committed
