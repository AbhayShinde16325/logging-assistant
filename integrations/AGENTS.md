# integrations/ — AGENTS.md

Owner: **Developer B**. Refines the root [`../AGENTS.md`](../AGENTS.md) without contradicting it.

## Module purpose

The only place that talks to Google Sheets: authentication (`client.py`), row↔object conversion
(`mapper.py`), CRUD behind the ports (`repository.py`), and manual-edit detection
(`reconciliation.py`). Business logic lives elsewhere.

## Read before coding

1. Root [`../AGENTS.md`](../AGENTS.md)
2. [`../skills/google-sheets-integration/SKILL.md`](../skills/google-sheets-integration/SKILL.md)
3. [`../docs/google-sheets-schema.md`](../docs/google-sheets-schema.md) — **authoritative** for tabs/columns
4. [`../docs/data-model.md`](../docs/data-model.md) and `../tasks.md`

## Layout

```text
integrations/google_sheets/
├── client.py           ← service-account auth + low-level get/values API wrappers (T-020)
├── mapper.py           ← rows <=> domain objects; empty-cell→null; degraded-cell flag (T-022)
├── repository.py       ← implements backend/app/services/ports.py (Task/Employee/Activity/Reminder) (T-023)
└── reconciliation.py   ← polling manual-edit detection per google-sheets-schema.md §3 (T-100)
```

## Hard module rules

- **Never trust row numbers as identity.** Find rows by matching `task_id`/`employee_id` in the
  `(A)` column — always. Stable generated IDs are created here at write time.
- Implement **only** the ports defined by Developer A in `backend/app/services/ports.py` — don't
  invent new public method names; coordinate (PR review by A) before changing any port signature.
- No imports from `frontend/`, `agent/`, `backend/app/services/` business modules — the backend
  imports this module; never the reverse (dependency direction, docs/architecture.md §3).
- All mutators also append a row to `Activity_Log` (task T-060) and `Command_Log` when invoked by
  a confirmed action — see sheets schema doc §1.
- Reconciliation: self-writes must not be flagged as manual edits (guard window per sheets-doc §3).
  Choose snapshot-compare polling (default) except with documented Apps-Script push, user can not
  wait (P2 idea, ADR-002).
- Quota discipline: batch reads/writes where easy; respect 60s poll default
  (`RECONCILIATION_POLL_SECONDS`).

## Conventions

- Full type hints; repository methods raise `Ports`-aligned exceptions (defined by A) on `NOT_FOUND`,
  then the routes map them to the error envelope.
- Unit tests use `FakeGoogleSheetsClient` (in `../tests/unit/`, T-030) — this module's tests must
  never require real credentials unless marked `integration` (opt-in flag).
- Credentials only via env (`GOOGLE_APPLICATION_CREDENTIALS` path); never hardcode, never log tokens.
