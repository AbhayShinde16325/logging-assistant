# ADR-002 — Google Sheets as the MVP Data Store

**Status:** Accepted · **Date:** 2026-11-09 · **Owner:** Developer B (with A)

## Context

MVP must persist employees, tasks, activity logs, reminders, and command records shared between an
assistant application and **humans editing the same data directly**. Team size: 3 employees (~10
laters). Constraints: free, local-first, no mandatory infra, and *human-editable is a feature*
(the team already coordinates in a shared spreadsheet).

## Options considered

1. **Google Sheets via service account + repository abstraction** ✅
2. SQLite/PostgreSQL server-side only
3. Airtable / Notion API
4. Flat files in a shared drive

## Decision

Use **Google Sheets** as the shared source of truth, accessed **only** through the
`integrations/google_sheets/` repository layer owned by B. Every other module speaks to interfaces
(`TaskRepository`, `EmployeeRepository`, `ActivityLogRepository`, `ReminderRepository`) defined by A
in `backend/app/services/ports.py` — storage is swappable by design.

## Why Sheets fits the MVP

- The existing workflow already lives in spreadsheets; human manual edits remain possible and must
  be respected (reconciliation is a **requirement**, FR-31, not an accident).
- Zero infrastructure; free; instant multi-user read/write; service-account auth is simple.
- Sheets API limits are far above MVP scale (≤10 employees, dozens of tasks, ~60s reconciliation
  polling).

## Consequences

- **No transactions, no constraints** — the app must enforce uniqueness/FK-validity itself
  (`duplicate rule`, `EMP-` resolution at execution time; `docs/data-model.md`).
- **ID management**: stable generated IDs (`TASK-*`), never row numbers (row order is not identity).
- **Polling-based reconciliation** (~60s): manual edits detected by comparing snapshots; documented
  limitations in `docs/google-sheets-schema.md` §3 (not instant; no server push).
- Google Apps Script (`onEdit`-based push) is a **documented future option** (schema `§3`), not an
  MVP requirement; the polling design doesn't depend on it.
- **-Consistency window** exists (app/assistant state lags manual edits by ≤ 1 poll interval —
  acceptable for this MVP and communicated to users via the warning in the recap UI).

## Migration path

The repositories are the only storage-aware code. Moving to PostgreSQL (future) = implementing the
same ports against a real DB and a one-time data migration script from Sheets; **no business rules,
routes, or agent code change**. Do not let ad-hoc Sheets access creep into `backend/app/services/`.

## Explicitly not in the MVP

- Google Apps Script web hooks / triggers, historical audit sheets, per-row lookups against
  additional tabs, spreadsheet formulas as application logic.

## Alternatives revisited

If quota/validation pain grows (concurrency edits > 10 concurrent users, multi-write batches
> 60 req/min), revisit ADR-002 → PostgreSQL first, Sheets becomes an import/export target.
