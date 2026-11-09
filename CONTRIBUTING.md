# CONTRIBUTING.md — Team Collaboration Rules

Three developers work in this GitHub repository, each with their own AI coding agent. The GitHub
repository is the **single source of truth**; imagine every PR as the only shared meeting room.

## Ground rules

1. The GitHub repository is the single source of truth. Local copies are only that — copies.
2. Every developer clones the **same repository** (never fork/rewrite; personal scratch repos are fine
   for experiments but deliver code through this repo's branches).
3. Every developer works on an individual feature branch; nobody shares a working directory or a
   checkout (rule 12 below is absolute).
4. Read `AGENTS.md` before starting — every session. AI agents read it automatically; humans should too.
5. Read the skill associated with your task (`skills.md` index → `skills/*/SKILL.md`).
6. Shared contracts (`contracts/`, `docs/api-contracts.md`, root docs, `.env.example`) must be agreed
   upon **before implementation starts**; changes afterwards require a coordinated PR + team ack.
7. Module ownership must be respected (map in `tasks.md` §1). Owners review all changes to their modules.
8. PRs must identify the affected modules in the template.
9. Every PR must include test results (CI run link or pasted output). Merge only with passing tests.
10. Changes to shared schemas require coordination — update JSON Schema + Pydantic + TypeScript in one PR.
11. AI coding agents must not independently rewrite repository architecture; architects (A) approve
    anything beyond the documented boundaries.
12. Never use the same working directory for multiple developers simultaneously. One clone per person,
    one branch per clone.

## Setup on a fresh machine

```bash
git clone https://github.com/AbhayShinde16325/logging-assistant.git
cd logging-assistant
git checkout develop && git pull origin develop
cp .env.example .env        # then edit values (Windows: Copy-Item .env.example .env)
bash scripts/setup_dev.sh   # Windows: .\scripts\setup_dev.ps1
```

## Daily workflow

```bash
# 0. Start from the latest integration branch
git checkout develop && git pull origin develop

# 1. Create your feature branch from develop (feature/<developer>/<name> or fix/...)
git checkout -b feature/a/confirmation-endpoints

# 2. Build, run focused tests
cd backend && pytest tests/unit -k confirmation

# 3. Commit in small, logical steps
git add <files>                       # never `git add .` blindly near module boundaries
git commit -m "Add confirm/reject endpoints with action validation"

# 4. Keep your branch current with develop
git fetch origin
git rebase origin/develop             # resolve conflicts with the module owner, never silently

# 5. Push your branch (never main / develop directly)
git push -u origin feature/a/confirmation-endpoints

# 6. Open a pull request INTO develop (GitHub UI, or `gh pr create --base develop`)

# 7. After merge, refresh develop locally
git checkout develop && git pull origin develop
```

## Current working on someone else's branch?

If you need an unfinished change from another developer, ask them to open a draft PR and rebase your
work on top of theirs — never commit into their branch.

## Branch & merge strategy (recommended for a 3-person team)

- `main` — protected, tagged releases ("prototype demo" cuts). Only `develop` merges into it, via PR.
- `develop` — integration branch. All feature work merges **here** through PRs; trunk is kept green
  (anything failing tests is reverted rather than tolerated).
- **Squash-merge** feature PRs into `develop` (one commit per feature keeps history reviewable).
- Merge order rule: module owners review their own modules; A reviews anything touching shared
  contracts; no self-merge without approval when other modules changed.
- Weekly-ish `develop → main` merge for demo milestones.
- Rationale: with three people, rebase-on-feature keeps integration friction low and the squash keeps
  `develop`'s history linear and readable by any AI agent later.

## PR checklist (template auto-inserted)

- Modules affected + ownership acknowledged
- Tests pass (unit; contract where relevant; integration when touching Google Sheets — mocked in CI)
- Contracts synchronized (JSON Schema / Pydantic / TypeScript)
- Docs updated (`docs/*.md`, `.env.example`, module `AGENTS.md`)
- No secrets or new undocumented dependencies
- `tasks.md` status updated

## Issue templates

Bugs: `.github/ISSUE_TEMPLATE/bug_report.md` · Feature requests:
`.github/ISSUE_TEMPLATE/feature_request.md`. Reference a task ID from `tasks.md` when applicable.
