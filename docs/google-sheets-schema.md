# Google Sheets Schema

Google Sheets is the MVP's **shared source of truth**. This document defines every tab and column;
the repository/mapper code (`integrations/google_sheets/`, Developer B) implements exactly this —
no extras without updating this file and ADR-002.

## 1. Workbook & tabs

Create exactly five tabs, named exactly as below, each with a **single header row frozen in row 1**.
`_Config` (optional tab 6) stores `schema_version=1` for reconciliation heuristics.

### `Employees`

Employees are the **only records maintained manually** in the sheet (no admin API in MVP;
see `Could-change ADRs` in ADR-002).

Cell A1:F1 exactly:

```text
employee_id | name | email | role | created_at | output_format_version
```

| Col | Field | Type | Req. | Meaning |
|---|---|---|---|---|
| A | employee_id | string `EMP-###` | ✅ | Stable primary key (see data-model). |
| B | name | string | ✅ | Unique display name. |
| C | email | string | ✅ | Unique. |
| D | role | string | ✅ | Free text ("Engineer"). |
| E | created_at | ISO 8601 UTC | ✅ | Row added time. |
| F | output_format_version | `1` | ✅ | Marker only — never counted as a "missing" cell. |

### `Tasks`

A1:L1 exactly:

```text
task_id | title | description | assignee_id | created_by | status | priority | due_date | created_at | updated_at | source | external_reference
```

| Col | Field | Type | Req. | Meaning |
|---|---|---|---|---|
| A | task_id | `TASK-`+8hex | ✅ | Primary key; generated at creation; one task per row, stable. |
| B | title | string | ✅ | Unique-ish per assignee + open status (duplicate rule in data-model.md). |
| C | description | string | ❌ | May be empty cell → `null`. |
| D | assignee_id | `EMP-###` | ✅ | FK (consistency with Employees; sheet-side dropdown data validation). |
| E | created_by | `EMP-###` | ✅ | FK. |
| F | status | enum text | ✅ | `TODO,IN_PROGRESS,BLOCKED,DONE,CANCELLED` (	if modified manually by a human → detected via reconciliation). |
| G | priority | enum text | ✅ | `LOW,MEDIUM,HIGH`. |
| H | due_date | date `YYYY-MM-DD` | ❌ | Empty = none. |
| I | created_at | timestamp | ✅ | Set by app at creation. |
| J | updated_at | timestamp | ✅ | Set **only** by the app on app-side updates; a stale/absent J + row content drift is the manual-edit signal. |
| K | source | enum text | ✅ | `CHAT,VOICE,MEETING,MANUAL_SHEET,API`. |
| L | external_reference | string | ❌ | Free-form pointer. |

### `Activity_Log`

A1:G1 exactly: `activity_id | employee_id | task_id | activity_type | description | timestamp | source` —
types/rules per [`data-model.md`](data-model.md). Append-only (the app never edits old rows).

### `Reminders`

A1:G1 exactly: `reminder_id | task_id | employee_id | scheduled_at | status | created_at | (none)` —
when the reminder loop transitions a row it updates the `status` cell in place (that is the only
in-place status change the app makes outside the Tasks tab).

### `Command_Log`

A1:H1 exactly:

```text
command_id | timestamp | employee_id | conversation_id | raw_message | proposed_actions COUNT | command_status | executed_action_ids
```

Do not treat **row numbers as identifiers** — any consumer present in the consumers is by matching
column A unconditionally.

### `_Config`

A1:B2: `schema_version | 1` — read once per process start; if version > code-supported, routes return
`503 INTEGRATION_ERROR` until B updates the code (conservatively refusing to write).

## 2. Rows ↔ objects: rules for the mapper (Developer B)

| Cell value | Mapped value |
|---|---|
| Empty string / whitespace-only | `null` for optional fields; validation error for required |
| Unparseable date in H | reconciliation flags row and marks `degraded`, the API returns `422` for that row when listing and the frontend shows a warning icon |
| Extra columns beyond L | ignored (forwards compatible) |
| Duplicate `task_id` in A | first occurrence (by row number) is authoritative, later duplicates are surfaced in `INTEGRATION_ERROR` details |

## 3. Reconciliation of manual edits (Developer B owns)

Goals: (a) detect manual changes quickly via polling; (b) avoid the app's own writes being mistaken
for edits; (c) resolve conflicts deterministically.

- **Detection (poll ~60s, `RECONCILIATION_POLL_SECONDS`):** snapshot each Tasks row (`task_id`, fields,
  `updated_at`) → compare with the cache; a human's edit leaves `updated_at` unchanged or back-dated
  while content differs → classify as `MANUAL_SHEET_EDIT`, write an Activity_Log entry, and pass the
  new state back to the conversation layer ("Task X was edited directly in the sheet").
- **Guard against self-race:** the writer stamps `updated_at` immediately before the row is flushed;
  the poller ignores any row whose `updated_at` is within the last ~5s.
- **If apps writes conflict** (command executing while the row also changed manually): **manual edit
  wins in scope of the row's content; the app's write proceeds on other rows**; a `WARN` entry is
  logged — the simpler consistent rule vs. last-writer-wins, given we don't have ETag support on
             arbitrary cell ranges for this operation type (limited Sheets API race surface).
- **Deleted rows (`GET /task/{id}` → 404)**: mark `task_id` as vanished in reports returned by chat
  queries, log `MANUAL_SHEET_EDIT` with description "Row removed manually in sheet".
- **Duplicates**: title+assignee+open-status duplicate search occurs at CREATE_TASK time.

> **Limitations (accepted in the MVP):** polling is not instant (≤60s); repeated re-fetching is
> cheap at our scale (≤ 10 employees, dozens of tasks); there is no server push webhook — the
> optional Apps Script (`onEdit`) approach is documented in ADR-002 but not required for the MVP.

## 4. Auth & permissions (Developer B)

- Service account **must not** be exposed to the frontend (never shipped in the SPA bundle).
- The service account needs "Editor" access to that single spreadsheet only.
- Quota: user-supplied limit fine for our request volume; check batch limits before arrays grow.
