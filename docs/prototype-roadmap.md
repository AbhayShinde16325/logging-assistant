# Prototype Roadmap

Priority tiers are **strict phases**: P0 must be demoable end-to-end before significant P1 work;
P1 before widespread P2 work. Nothing here overrides `tasks.md` (the live board) — this file is the
**why**; `tasks.md` is the **what/who**.

## P0 — Essential (the first working prototype)

| # | Feature | Owner |
|---|---|---|
| 1 | Backend running (FastAPI `/api/v1` + health) | A |
| 2 | Frontend running (Vite React shell) | C |
| 3 | Text chat end-to-end (message → reply) | A+C |
| 4 | Structured task extraction | A |
| 5 | User confirmation flow (propose → confirm/reject) | A |
| 6 | Google Sheets task creation | A+B |
| 7 | Task listing | A+B+C |
| 8 | Task completion (status update via chat) | A |
| 9 | Employee identification & task assignment | A |

**Exit:** the exact demo flow in `docs/testing-strategy.md` §*demonstration* works on
development machines, with unit+contract tests green.

## P1 — Important (prototype robustness and tracking)

| # | Feature | Owner |
|---|---|---|
| 1 | Voice input (browser capture, Web Speech API) | C |
| 2 | Activity logging on every state change | A+B |
| 3 | Manual Google Sheets edit detection + reconciliation (~60s poll) | B |
| 4 | Basic reminders + reminder scheduler loop | A+B |
| 5 | Employee-wise task dashboard | C |

**Exit:** demo includes voice input, manual sheet edits reflected in the app within 60s, reminders
firing while the backend runs, dashboard counts consistent with the sheet.

## P2 — Future (post-prototype; do NOT start until P1 exit)

| # | Feature | Note |
|---|---|---|
| 1 | Meeting transcript processing | Pasted text → extracted actions; P2 (FR-33) |
| 2 | Automatic meeting joining | Explicitly out of the MVP; largely a trust/ToS + P2 item |
| 3 | Advanced analytics | Beyond the dashboard summary |
| 4 | Calendar integration | Replaces date markdown parsing (only if validation pain persists) |
| 5 | More agent autonomy | e.g. batching confirmed actions, destructive auto-runs — requires an ADR |
| 6 | PostgreSQL migration | The repository ports already abstract storage (ADR-002) |
| 7 | Multi-team support | Data model gains a `team_id`; out of MVP scope |

**Hard rule:** P1 and P2 work must never block the P0 prototype. If P0 is delayed, park the P1/P2
task in a `feature/…` branch and do not merge anything beyond stub implementations.

## Sequencing & integration checkpoints

```text
M0 (done)   Repo foundation, contracts, task allocation, review sign-off                — A,B,C
M1          Independent scaffolding: backend+agent (A), sheets client (B), UI shell (C) — parallel
M2          Core feature runs per module: agent extraction+confirm (A), CRUD (B), chat+list UI (C) — parallel
M3          Wiring: agent ↔ service ↔ sheets repos ↔ frontend                           — mostly A with B/C points of contact
M4          Reminders, reconciliation polling, voice, dashboard                         — parallel, meeting-extraction stays P2
M5          Testing, demo scenarios, polish, README honesty pass                        — all three
```

Any milestone-appropriate scaling decision (e.g., Reminders P1 → dashboard P1 order swapping)
must be recorded in `tasks.md` — never re-scoped silently in code.
