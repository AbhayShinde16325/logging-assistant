# ADR-001 — Monorepo Architecture

**Status:** Accepted · **Date:** 2026-11-09 · **Owner:** Developer A

## Context

Three developers (A: backend+agent, B: Google Sheets integration, C: frontend+voice) work in one
GitHub repo with AI coding agents. Concerns are clearly separable, cross-module integration is a
regular occurrence, and coordination cost must stay low.

## Options considered

1. **Monorepo with per-module `AGENTS.md` + ownership map** ✅
2. Three separate repos per module
3. Single-repo single layer (one Python package doing everything)

## Decision

Use a monorepo (`logging-assistant`) laid out as: `backend/`, `agent/`, `integrations/`, `voice/`,
`frontend/`, `tests/`, plus shared `contracts/`, `docs/`, `skills/`. Each module has its own
`AGENTS.md` refining the root one; `tasks.md` §1 is the file-level ownership map.

## Rationale

- **Contracts live next to code** (`contracts/`, `docs/api-contracts.md`), so a single PR can
  synchronize JSON Schema + Pydantic + TypeScript atomically — impossible across 3 repos.
- **One clone, one branch model** (`CONTRIBUTING.md`) keeps the 3-person workflow trivial.
- **AI agents benefit**: root `AGENTS.md` + module `AGENTS.md` + `SKILL.md` gives each agent a local
  instruction set without limitless global files.
- Cross-module refactors (e.g. renaming a field) become one atomic commit.

## Consequences & rules

- Strict dependency direction (`docs/architecture.md` §3); module-internal imports only — a module
  depends on another module's ports, not internals.
- Ownership boundaries are enforced in review, not tooling; every PR lists affected modules.
- CI (`.github/workflows/ci.yml`) runs backend + frontend + contract validation independently.
- Costs: larger clone, occasional lockfile merge friction — accepted for a 3-person team.

## Alternatives revisited later

If the frontend/agent teams grew beyond ~4 people each, split repos at that point; the ports
(`TaskRepository`, etc.) are designed to keep that cheap.
