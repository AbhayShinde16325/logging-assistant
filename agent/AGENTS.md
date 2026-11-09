# agent/ — AGENTS.md

Owner: **Developer A**. Refines the root [`../AGENTS.md`](../AGENTS.md) without contradicting it.

## Module purpose

Pure **reasoning** orchestration (LangGraph): turn a normalized user message + request context into
validated `proposed_actions` and a reply. This module never executes actions, never writes to Google
Sheets, and never authorizes anything.

## Read before coding

1. Root [`../AGENTS.md`](../AGENTS.md) §4 (AI agent rules)
2. [`../skills/agent-development/SKILL.md`](../skills/agent-development/SKILL.md)
3. [`../docs/agent-workflow.md`](../docs/agent-workflow.md) — state shape, node table, error/retry table
4. [`../contracts/agent-action.schema.json`](../contracts/agent-action.schema.json)

## Layout

```text
agent/app/
├── graph.py        ← StateGraph assembly; single entry point run_chat(state) (T-013)
├── state.py        ← AgentState TypedDict exactly as in ../docs/agent-workflow.md §2
├── nodes/          ← one file per node; deterministic nodes must import nothing from LLM SDKs
├── prompts/        ← versioned prompt templates + extraction fixtures for tests
├── models/         ← BaseModelProvider protocol + OllamaProvider + MockModelProvider (T-014)
├── tools/          ← intentionally EMPTY in the MVP (placeholder; see workflow doc §6)
└── workflows/      ← chat_workflow.py (MVP), meeting_extraction_workflow.py (P2)
```

## Hard module rules

- **Zero side effects.** No network writes anywhere; the only outbound HTTP is the model provider
  call for Ollama, and file I/O is none.
- Imports allowed: stdlib, pydantic, langgraph, httpx (inside `models/`), local `nodes/prompts/models`.
  Forbidden: `backend.app.*`, `integrations.*`, `voice.*` — the backend imports **this** module,
  never the reverse.
- Deterministic nodes (`resolve_employees`, `resolve_dates`, `validate_and_propose`) are pure
  functions and must be unit-testable with no model provider at all.
- All LLM outputs flow through Pydantic parsing; JSON parse failure → 1 corrective retry →
  clarification reply; never fabricate IDs or enums (`AGENT_PROMPT_TESTING` fixtures in `prompts/`,
  contract-shape checks in `../tests/contract/`).
- Model/provider changes = config (`MODEL_PROVIDER`, `OLLAMA_MODEL`) — no business-logic edits.

## Conventions

- Full type hints; nodes are small, named, single-purpose; state updates return partial dicts.
- Every prompt string lives in `prompts/` with a version comment + date; prompts produce **draft
  structures**, final truth belongs to app resolution nodes.
- Tests: fixtures + `MockModelProvider` in `../tests/unit/agent/`; no real LLM in unit/contract runs.
