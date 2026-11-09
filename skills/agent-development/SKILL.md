# SKILL: Agent Development

> **DE (skill-steward):** Developer A · Applies to: `agent/**` contributors (and reviewers).

## 1. Skill purpose

Implement the LangGraph workflow: state management, structured extraction, entity/database
validation, proposed-action generation, confirmation surfacing, and the model-provider abstraction —
while keeping the LLM sandboxed from side effects.

## 2. When the agent should use this skill

Any task touching `agent/**`; also when adding an intent/action type (coordinate contract change).

## 3. Relevant directories and files

- Code: `agent/app/` (`graph.py`, `state.py`, `nodes/`, `prompts/`, `models/`, `tools/`, `workflows/`)
- Spec: `../docs/agent-workflow.md` (**authoritative**), decision: `../docs/decisions/ADR-003-agent-orchestration.md`
- Contracts: `../contracts/agent-action.schema.json`, `../contracts/chat-*.schema.json`
- Tests: `../tests/unit/agent/*`, `../tests/contract/test_chat_flow.py`

## 4. Technology-specific implementation rules

- **State is append-only per workflow doc**: nodes return partial-dict updates; `proposed_actions`
  appear **only** after validation — never from raw model text.
- **LangGraph graph**: node registry + deterministic edges; `UNKNOWN` intent path returns a
  clarification-only response. No conditional edges jumping straight to execution.
- **Structured output pattern**: strict prompt shape → parse with Pydantic → parse failure = one
  corrective retry mentioning the schema violation → failure becomes a clarification reply or
  `MODEL_ERROR`; the graph **never** ships `entities` upstream as-is.
- **Model-provider abstraction**: `agent/app/models/` defines the protocol; `OllamaProvider` uses
  plain HTTP (`httpx`) against `OLLAMA_BASE_URL` + `/api/chat`/`/api/generate` with `format:"json"`;
  `MockModelProvider` for tests. Provider changes must not touch nodes/graph/business. A future
  provider (OpenAI-compatible) = new class in the same package (check `response_format` support
  before claiming it — do not invent capabilities).
- **Temperature 0** for classification/extraction; prompts versioned as files with fixtures in
  `prompts/` + linked tests.
- **Deterministic nodes** resolve everything the full data model needs: EMP resolution via repository
  data passed in (never from the model), date phrase → ISO `YYYY-MM-DD` anchored to server clock
  "today".
- **Confirmation**: `requires_confirmation` derives from the action-type table (workflow doc §3);
  pending actions are stored in the backend (not the graph).

## 5. Coding conventions

Full type hints; pure deterministic functions; `snake_case` node names; one node per file; state
mutations only add/replace own keys; all error rows include the node name in `error` for debuggability.

## 6. Dependencies and interfaces

- Allowed imports: stdlib, pydantic, langgraph, httpx (inside `models/` only), local modules.
  Forbidden: `backend.*`, `integrations.*`, `voice.*`, `frontend`.
- The **only interface contract** with the backend is: input `AgentState`-shaped dict (message,
  `employee_id`), output a validated `ChatResponse` data model — see `contracts/`.
- Adding a new `action_type` requires the coordinated contracts PR (JSON Schema + enums + docs).

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Trusting model dates/IDs/enums | Resolve through deterministic nodes against repository data |
| Model failure → invented reply content | Templates/fallback replies; explicit clarification questions |
| Side effects inside nodes (calls, writes) | Nodes are pure; only `models/` reaches the network |
| Prompt edits without fixtures | Every prompt change ships/updates ≥ 1 fixture test |
| Scope creep: TLS user auth inside graph | Not here. The route layer handles auth, DI config, storage boundaries Agent uses |

## 8. Testing requirements

- Fixtures & `MockModelProvider` for all unit tests (no live model).
- Deterministic nodes tested for: employee ambiguity, unknown employee, unparseable dates,
  duplicate-title detection hooks (surface validation issue, do not propose).
- End-to-end (contract test): `/chat` with mocked provider produces `proposed_actions` matching the
  schemas; invalid-model-output path gracefully degrades.

## 9. Completion checklist

- [ ] `docs/agent-workflow.md` updated in the same PR if node/state/prompt semantics changed
- [ ] Structured outputs remain schema-valid (schema files untouched or coordinated)
- [ ] No node reaches the network except through `models/`
- [ ] Unit + contract tests incl. ≥ 1 model-failure fallback path
- [ ] New env vars (model config) documented in `.env.example`
