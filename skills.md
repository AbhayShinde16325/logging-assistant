# Skills System — Project-Specific Skills Index

This is the **index** of all project-specific skills. Each skill lives in its own directory with a
conventional `SKILL.md` file. AI coding agents must read the relevant `SKILL.md` *before*
implementing a feature in that area, alongside the root [`AGENTS.md`](AGENTS.md).

## How to use

1. Identify the skill matching your task (tables below).
2. Read `skills/<skill-name>/SKILL.md` fully.
3. Cross-check the authoritative docs it references (architecture, API contracts, data model).
4. Follow the skill's coding conventions and completion checklist; treat the checklist as part of
   the Definition of Done in the root `AGENTS.md` §6.

## Core architecture skills (all developers)

| # | Skill | File | Purpose |
|---|-------|------|---------|
| 1 | Project Architecture | [`skills/project-architecture/SKILL.md`](skills/project-architecture/SKILL.md) | Understand the monorepo, module boundaries, dependency direction, shared contracts, and ownership before touching anything. |

**Use it when:** starting any task for the first time, creating new modules, or when a change might
cross a module boundary.

## Backend & agent skills (Developer A, readable by all)

| # | Skill | File | Purpose |
|---|-------|------|---------|
| 2 | FastAPI Development | [`skills/fastapi-development/SKILL.md`](skills/fastapi-development/SKILL.md) | Routes, schemas, services, validation, error handling, and tests for the `/api/v1` API. |
| 3 | Agent Development | [`skills/agent-development/SKILL.md`](skills/agent-development/SKILL.md) | LangGraph workflows, state, structured extraction, tool boundaries, confirmation nodes, model-provider abstraction. |

## Integration skills (Developer B, readable by all)

| # | Skill | File | Purpose |
|---|-------|------|---------|
| 4 | Google Sheets Integration | [`skills/google-sheets-integration/SKILL.md`](skills/google-sheets-integration/SKILL.md) | Authentication, reading/writing task records, reconciliation of manual edits, repository patterns. |

## Frontend & voice skills (Developer C, readable by all)

| # | Skill | File | Purpose |
|---|-------|------|---------|
| 5 | Frontend Development | [`skills/frontend-development/SKILL.md`](skills/frontend-development/SKILL.md) | React components, API services, state management, loading/error states, dashboard. |
| 6 | Voice Processing | [`skills/voice-processing/SKILL.md`](skills/voice-processing/SKILL.md) | Voice capture, transcription abstraction, validation, chat-workflow integration. |

## Cross-cutting skills (all developers, required before merging)

| # | Skill | File | Purpose |
|---|-------|------|---------|
| 7 | Testing and Integration | [`skills/testing-and-integration/SKILL.md`](skills/testing-and-integration/SKILL.md) | Unit/contract/integration tests, mocking LLM & Google Sheets, cross-module validation. |

## Rules that apply to every skill

- Never modify a `SKILL.md` or shared contract without coordinating with the module owner (A for
  shared files; otherwise the DE listed in the skill's front-matter).
- Never implement a capability the skill or contract does not describe (scope control).
- The root `skills.md` is an index only — the individual `SKILL.md` files are authoritative for
  implementation detail.
