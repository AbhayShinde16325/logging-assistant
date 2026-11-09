# SKILL: Project Architecture

> **DE (skill-steward):** Developer A · Applies to: everyone · Skill completion counts toward
> Root AGENTS.md DoD (`AGENTS.md` §6) for all tasks.

## 1. Skill purpose

Enable any developer's AI coding agent to (a) understand this monorepo's layout, (b) place new code
in the correct module, (c) respect dependency direction and ownership, (d) use shared contracts
instead of improvising.

## 2. When the agent should use this skill

Start **every** task here at least once per repository, and always when: creating files/directories,
adding dependencies, or handling changes that touch more than one module.

## 3. Relevant directories and files (read in this order)

1. Root `AGENTS.md` (whole object)
2. `docs/architecture.md` — especially §2 table & §3 dependency direction
3. `tasks.md` §1 ownership map; your milestone's table
4. `docs/data-model.md` + `contracts/README.md` (ID/enums/formatting conventions)
5. If your change crosses modules: the module `AGENTS.md` **of each touched module**
6. ADRs that constrain the decision area you are in (`docs/decisions/`)

## 4. Implementation rules

- **Dependency direction is one-way**: the backend imports `agent`, `integrations`, `voice`; none of
  these ever import `backend`, `frontend`, or each other. Violation = rejected PR even if tests pass.
- Cross-module calls use **ports** (defined in `backend/app/services/ports.py` and implemented by B's
  repositories to match) — never concrete classes.
- New shared code (errors, IDs, dates) goes into well-named util modules only once
  (`backend/app/utils/`); duplicating helpers "for convenience" in another module is banned.
- A directory exists only with its documented purpose; empty scaffolding must include a comment or
  `.gitkeep` + future responsibility note (frontend/src/README.md is an example).
- Contracts as source of truth: schema files in `/contracts/`; definition changes must be proposed
  **before code**, then synchronized in one PR (JSON Schema ↔ Pydantic ↔ TS in lock-step).

## 5. Coding conventions (cross-module)

- Python & routes: `snake_case`; TS: `camelCase`; components/classes: `PascalCase`.
- IDs & dates: prefixes (`EMP-`, `TASK-`, `REM-`, `ACT-`, `LOG-`, `CONV-`), `YYYY-MM-DD`, UTC ISO 8601.
- Module boundaries tracked in `tasks.md` §1 — invoke the owner in PRs.

## 6. Dependencies and interfaces

- New **runtime** dependency ⇒ exact purpose in the PR + matches the stack table in root `AGENTS.md`
  §"Technology stack" or an ADR is written first.
- New **port** ⇒ proposal PR referencing `docs/architecture.md` §3 diagram update.

## 7. Common mistakes to avoid

| Mistake | Correct action |
|---|---|
| Importing concrete Sheets/Ollama classes from `backend/app/services/` | Use the port, wire the concrete class only in `backend/app/api/dependencies.py` and confirm the cost of what's imported |
| Migration-script-style ad-hoc Sheets writes in tests/community fixes | Use the repository/mapper; fake client for tests |
| Renaming contract fields in TS only, or Pydantic only | Propose contract change → update all three layers in one PR |
| New util duplicated per module | Move to backend utils (or contracts examples) once |
| Creating a new top-level package for a one-off idea | Place it in an existing documented module; unnecessary layers are removed in review |

## 8. Testing requirements

- If you move code across modules (boundary-affecting), contract tests in `tests/contract/` must
  stay green — they indirectly enforce the dependency direction.
- Run `python scripts/validate_contracts.py` after any `/contracts/` edit.

## 9. Completion checklist

- [ ] Root + module `AGENTS.md` updated if the module boundary/ownership meaning changed
- [ ] Architecture diagram updated when a boundary changed (`docs/architecture.md` §2/§3)
- [ ] No dependency-direction or ownership violations (checked in review)
- [ ] `tasks.md` touched-task IDs and statuses current
