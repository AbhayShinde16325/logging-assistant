# ADR-003 — Agent Orchestration with LangGraph

**Status:** Accepted · **Date:** 2026-11-09 · **Owner:** Developer A

## Context

The assistant must turn free-form text/voice input into structured, validated, confirmable actions,
work with a **locally running LLM** (free/local-first constraint), stay flexible on model choice, and
never grant the model write access to Google Sheets.

## Options considered

1. **LangGraph state machine (graph of nodes incl. deterministic ones) + custom model protocol** ✅
2. LangChain chain-of-prompts in a single function
3. Hand-rolled interpreter over LLM JSON calls
4. CrewAI / AutoGen multi-agent frameworks
5. OpenAI Assistants-style tool loop (cloud platform)

## Decision

Orchestrate the flow (`docs/agent-workflow.md`) as a **LangGraph** `StateGraph` in `agent/app/graph.py`
with explicit nodes: `normalize_input → classify_intent (LLM) → extract_entities (LLM) →
resolve_employees (deterministic) → resolve_dates (deterministic) → validate_and_propose
(deterministic) → compose_reply (LLM, with template fallback)`. The model is accessed only through
`agent/app/models/` (`BaseModelProvider` protocol with `OllamaProvider` first),
configured via env (`MODEL_PROVIDER`, `OLLAMA_MODEL`, `LLM_TIMEOUT_SECONDS`).

## Rationale

- **Mixed graphs work best in our flow**: most steps are deterministic; only classification,
  extraction, and phrasing need the LLM. A graph makes these different step types explicit.
- **LangGraph is open-source and composable**; state (`AgentState`) is typed, checkpointing is
  available if we later add multi-turn memory (out of MVP scope).
- **Provider abstraction is ours**: no LangChain-model-specific coupling beyond the call boundary;
  swapping Ollama for an OpenAI-compatible endpoint is a config change + new class.
- **The trust boundary is structural**: the graph only ever emits `ProposedAction` data (Pydantic
  entities validated against `contracts/agent-action.schema.json`); execution/confirmation happens
  in backend HTTP flows with no agent code in the path (see `api-contracts.md` actions).

## Framework choice rationale (vs alternatives)

- Simple chain (option 2) can't branch cleanly to clarify-or-propose paths.
- Hand-rolled (option 3): fine for adjacent flows but reinvents state/error plumbing; LangGraph
  gives it with less code.
- Multi-agent frameworks (option 4): overkill; framework lock-in with weak typing.
- Cloud assistant loops (option 5): conflicts with the **local-first** constraint.

## Consequences / trade-offs

- Deterministic validations duplicate LLM extraction effort (e.g. employees resolved both in LLM
  output and our resolver node) — a **deliberate zero-trust** duplication, not waste.
- Prompt-version updates are code changes requiring test fixtures (`docs/testing-strategy.md` §
  risk-mitigation).
- Offered fallback: if `temperature=0` + a well-shaped rag output misses >30% in dev validation
  testing budget for Milestone 2, the team may revisit extraction UX (not the ADR).

## Alternatives revisited later / pitfalls closed

- If support for a *second* remote LLM provider is required, provider interfaces stay intact —
  no ADR needed — but the JSON-output-shape contract (`agent-action` structure) requires
  `language: '{"type":"object"}'`-style mode; care must be taken for providers that don't support
  `response_format` — the next ADR decides.
