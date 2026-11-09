# Agent Workflow — LangGraph Orchestration

Owner: Developer A. The `agent/` module implements this document. The LLM **reasons**; the backend
**validates and executes**; integration write access lives only in `integrations/google_sheets/`.

## 1. Workflow diagram

```text
User Input
    |
    v
Input Normalization
    |
    v
Intent Classification ---------------------- (LLM, structured JSON)
    |
    v
Structured Information Extraction ---------- (LLM, structured JSON)
    |
    v
Employee and Task Validation --------------- (deterministic, app data)
    |
    v
Proposed Action Generation ----------------- (deterministic assembly + validation)
    |
    v
User Confirmation
    +---- Rejected ----> End (Command_Log = REJECTED)
    |
    v
Backend Action Execution ------------------- (route+service, independent of agent)
    |
    v
Google Sheets Integration
    |
    v
Activity Logging
    |
    v
Reminder Scheduling
    |
    v
Response to User
```

The MVP runs one chat turn per graph invocation. "User Confirmation → execution" is a **separate HTTP
request** (`POST /actions/{id}/confirm`), not a graph continuation — this is what keeps the agent from
being able to write anything by itself.

## 2. State structure (`agent/app/state.py`)

```python
class AgentState(TypedDict, total=False):
    raw_input: str            # verbatim user text
    normalized_input: str     # trimmed, lowercased copy for heuristics only
    employee_id: str          # caller (request-scoped, provided by route)
    intent: str               # CREATE_TASK | UPDATE_TASK | COMPLETE_TASK | ASSIGN_TASK |
                              # DELETE_TASK | CREATE_REMINDER | QUERY_TASKS | QUER Summary:Y_ACTIVITY |
                              # LOG_ACTIVITY | MEETING_EXTRACT | UNKNOWN
    entities: dict            # LLM-extracted draft fields (untrusted)
    proposed_actions: list    # validated ProposedAction objects (the trust boundary)
    validation_issues: list   # problems that force clarification chatter
    system_reply: str         # final message (template + LLM phrasing of a success)
    error: str | None         # node-level failure marker
```

Append-only: nodes read predecessors' outputs and add their own updates; LangGraph's state replacement
is source-of-truth tracking.

## 3. Nodes (`agent/app/nodes/`) — responsibilities

| Node | Type | Responsibility / LLM role |
|---|---|---|
| `normalize_input` | deterministic | Trim, unify whitespace, note the language; record `raw_input` unchanged for the Command_Log. |
| `classify_intent` | **LLM** | One classification with structured output: `{intent, confidence, missing_fields[], clarification?}`. Heuristic fix-ups (e.g. phrase "completed" → `COMPLETE_TASK`) applied **after** the model returns. |
| `extract_entities` | **LLM** | Structured extraction of candidate task fields: title, description, assignee name, due-date phrase, priority, status change, reminder phrase. Everything remains a **string draft** — dates/phrases are resolved by app code below. |
| `resolve_employees` | deterministic | Map person names to `EMP-…` using only `EmployeeRepository` data. Ambiguity → clarification; "me" → request-scoped `employee_id`. |
| `resolve_dates` | deterministic | Convert phrase → ISO `YYYY-MM-DD` anchored on "today" (server clock). Unresolvable → clarification ("Which date do you mean?"). |
| `validate_and_propose` | deterministic | Assemble 0..n `ProposedAction` objects using Pydantic validation + duplicate/task-existence checks via the ports; attach `requires_confirmation` per the action's `consequential` flag table. Zero valid actions → clarification reply (`requires_confirmation=false`). |
| `compose_reply` | LLM-light | Phrase the user's reply/clarification or the "task created" confirmation, using templates + followed LLM post-pass. LLM failure → deterministic template fallback (guaranteeing a response). |

### Confirmation mechanism

| Action type | Consequential? | requires_confirmation |
|---|---|---|
| `CREATE_TASK`, `UPDATE_TASK`, `DELETE_TASK`, `COMPLETE_TASK`, `ASSIGN_TASK`, `CREATE_REMINDER` | ✅ | true → user must call confirm/reject |
| `QUERY_TASKS`, `QUERY_ACTIVITY` | ❌ | false → answered inline in the same turn |

Pending actions live in the backend's in-memory store for 24h (`EXPIRED` afterwards) keyed by
`action_id` — a single source of truth for the confirm/reject endpoints (see `api-contracts.md`).

## 4. Models & structured output (`agent/app/models/`)

- `BaseModelProvider` protocol: `"chat_json" | "complete_json"`. Implementations:
  `OllamaProvider` via HTTP against `OLLAMA_BASE_URL` (no SDK needed) — the first class;
  others `Mock`, `OpenAICompatible` (future).
- Structured output pattern consolidated here: output the state, then use **Pydantic coercion** —
  parse errors → one retry conversationally → else `MODEL_ERROR` (never guess/abridge silently).
- `temperature=0` for both classification & extraction calls.
- Choosing a **model** or provider = env vars (`MODEL_PROVIDER`, `OLLAMA_MODEL`), not code edits.
- Never import model modules from `backend/app/services/` — pass through interfaces only.

## 5. Error handling & retry behavior

| Failure | Agent behavior | User-visible |
|---|---|---|
| LLM invalid JSON | 1 retry with corrective instruction | ask again gracefully / `503 MODEL_ERROR` after the retry |
| LLM timeout (60s) | 1 retry | ask again gracefully |
| Unknown employee/task in draft | clarification, not fabrication | "Which Rahul? EMP-002 ..." with candidates |
| Internally inconsistent request (e.g. complete an unknown task) | clarification | "I can't find task TASK-…" |
| Integration failure at execution | **not the agent's** — `POST /confirm` returns `502 INTEGRATION_ERROR`, action returns to `PENDING`, user may retry | error envelope |
| Internal bug in a node | graph middleware → `INTERNAL_ERROR` with node name | error envelope |

## 6. Tool boundaries

- The MVP graph uses **no external tool calls** (no browsing, no code execution, no auto-attached
  plugins). The only "tools" are app-side validators/deterministic nodes — controlled by us.
- If a future use case adds tools, they follow the same pattern: a `tools/` module per tool, a
  Pydantic-validated interface, no side-effectful APIs. (Placeholder: `agent/app/tools/`.)

## 7. Prompts (`agent/app/prompts/`)

- Versioned as files (`intent_prompts.py`, `extraction_prompts.py`); each prompt versioned with its
  last change date and kept in sync with this doc; every change to an extraction prompt needs an
  accompanying test fixture so regressions are visible.
- Prompts only ever produce the **draft structures**; final truth always comes from app resolution.
- Lookups (names/IDs) are resolved in the `resolve_employees` node, not by prompt context requiring
  the model to recall tables.

## 8. Workflows that *reuse* this graph (`agent/app/workflows/`)

- `chat_workflow.py` — the default above.
- `meeting_extraction_workflow.py` (P2): input = meeting text; same nodes minus confirmation on
  proposed actions (they follow normal confirm/reject individually), plus a `decisions/items` block
  surfaced separately in the API response.
