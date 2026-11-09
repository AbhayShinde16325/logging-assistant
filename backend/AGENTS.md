# backend/ — AGENTS.md

Owner: **Developer A**. Refines the root [`../AGENTS.md`](../AGENTS.md) without contradicting it.

## Module purpose

The FastAPI application: HTTP boundary, validation, service layer, and orchestration of everything
below it (agent, integrations, voice). **The backend owns the API** — `../docs/api-contracts.md`
is authoritative for every route.

## Read before coding

1. Root `AGENTS.md` (§3 API rules, §4 AI agent rules, §5 Git, §6 DoD)
2. `../skills/fastapi-development/SKILL.md`
3. `../docs/architecture.md` (§2–§5), `../docs/api-contracts.md`, `../docs/data-model.md`
4. `../tasks.md` (your task IDs: T-0*, T-1*.)

## Layout

```text
backend/app/
├── main.py                 ← app factory, routers, middleware, error handlers
├── api/
│   ├── routes/             ← one router per resource (chat, tasks, employees, activity,
│   │                          voice, dashboard, meetings, reminders, actions, health)
│   └── dependencies.py     ← DI: ports → repositories, model provider, services
├── core/
│   ├── config.py           ← pydantic-settings, all env vars from ../.env.example
│   └── security.py         ← optional bearer-token check (API_BEARER_TOKEN)
├── models/                 ← persistence-oriented domain models (dataclasses/pydantic)
├── schemas/                ← request/response Pydantic schemas mirroring ../contracts/
├── services/               ← business logic: task_service, chat_service, action_service,
│                              reminder_service, dashboard_service (ports: services/ports.py)
├── integrations/           ← thin typing/adapter glue; real Sheets code lives in ../integrations/
└── utils/                  ← ids, utcnow, error envelope builders — no business logic
```

## Hard module rules

- Routes are thin: parse (Pydantic) → call service → map result → respond. No repository/Sheets/LLM
  access in route bodies.
- Services depend only on **ports** (`services/ports.py`) and the agent graph interface — never on
  concrete Google/Ollama classes.
- Do **not** import from `../integrations/google_sheets/`, `../voice/`, or Ollama SDKs anywhere in
  `app/`. The wiring happens in `dependencies.py` at startup (concrete adapters injected into ports).
- Scaffold-first (T-010–T-015): ports + fakes **before** route implementations, so routes are
  unit-testable without Developer B's real repositories.
- Every non-2xx response uses the shared error envelope (handlers live in `main.py`).
- The agent graph output is never executed directly: confirm/reject endpoints receive `action_id`,
  re-validate against current repository state, then execute.

## Conventions

- Python 3.11+, Pydantic v2, full type hints, `ruff check`, `pytest` (unit + contract at repo root).
- New env var ⇒ add to `core/config.py` **and** `../.env.example` in the same PR.
- Naming: modules/files `snake_case`; one service class per domain object; fakes `Fake*`.
- Tests: `../tests/unit/` (fast, fake ports), `../tests/contract/` (TestClient + jsonschema).
