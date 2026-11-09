# Development Workflow — Day-to-Day for a Three-Person Team

Complements [`../CONTRIBUTING.md`](../CONTRIBUTING.md) with concrete setup steps and the branch model.

## 0. One-time environment setup (per developer, per machine)

```powershell
# 1. Clone from the single source of truth
git clone https://github.com/AbhayShinde16325/logging-assistant.git
cd logging-assistant

# 2. Base yourself on develop
git checkout develop && git pull origin develop

# 3. Environment file (fill values from .env.example comments)
Copy-Item .env.example .env
```

### Python backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pip install -r tests\requirements.txt        # pytest, pytest-asyncio, httpx, ruff, mypy
```

### Frontend

```bash
cd frontend
npm install
```

### Local services

- Ollama: `ollama pull llama3.1:8b` and `ollama serve` (or run it whenever needed).
- Google Sheets: create/copy the sheet once per developer (private copies during development)
  and create **one shared** sheet for integration tests with test employees only.

## 1. Branch model

```text
main                stable, tagged release cuts; ONLY develop merges in
develop             integration branch — target of all feature PRs
feature/<dev>/<n>   one branch per feature (branched from develop)
fix/<dev>/<n>       focused fixes
```

- `feature/a/task-crud-api` — Developer A feature naming example.
- Prefer short-lived branches (< ~3 days), squash-merge into `develop`, keep trunk green.
- If a change must land on `main` directly (rare hotfix), cherry-pick from `develop` and tag a patch.

## 2. Dependency order (critical for a small team)

```text
Milestone 0 (this repo's foundation PR) → contracts reviewed by all three.
Milestone 1 (parallel, no cross-reading of each other's modules):
  A: backend/agent scaffolding — routes + ports + config done first (unblocks B and C).
  B: Google Sheets integration against B's test sheet + mocked ports until A's server wiring.
  C: frontend scaffolding + static UI against mocked API until contracts compile.
Milestone 2+ (cross-module wiring only A does at first; B and C pair where needed).
```

Every cross-module touch needs the module owner as reviewer, and contract changes need **all three**
reviewed/acknowledged in the same PR (contract owners enforce this; A is the tie-breaker).

## 3. Contracts-first discipline

1. Need a new endpoint/field? **Propose first** in `docs/api-contracts.md` + `contracts/`.
2. In the same PR update: JSON Schema, backend Pydantic schemas, frontend TS types, this + ADR docs.
3. Keep `contracts/README.md`'s mapping table current so any future reader (or agent) can spot drift.

The backend will extend mocks until that PR lands; the frontend uses the typed contract shapes
(stub `services/` calls return fixtures) until they land.

## 4. Working directory rules (enforced)

1. One machine clone per person — never share a working directory or "hand over" your checkout.
2. Never push to `main` or `develop` directly; PRs only.
3. Rewriting history: allowed **only** on your own unpushed branch; never rebase others' branches.
4. `fix/` branches must not silently revert other developers' commits; conflicts → coordinate with owner.
5. Never commit: `.env`, service-account JSONs, node_modules, dist artifacts (`.gitignore` covers
   both, but double-check before `git add`).
6. Depend only on API contracts, not on internal module code (importing across module boundaries
   requires an ADR + owner review).

## 5. Local consistency loop (each developer, before every push)

```bash
backend/:  pytest tests/unit -q          && pytest tests/contract -q
frontend/: npm run lint                  && npx tsc --noEmit             && npm run build
contracts: python scripts/validate_contracts.py
```

CI must be green before merge; the module owner merges after review (squash).

## 6. Merge etiquette

- Keep branches small (< ~400 changed lines when possible); giant PRs stall 3 people.
- Squash-merge keeps `develop` history: one commit per feature with a clear message referencing the
  task ID (`tasks.md`).
- `docs/*.md` + root files are also owner-reviewed (shared files owner: Developer A).
- When B/C/A's work overlaps a shared file: first to PR is basis; later organization rebases cleanly.
- Conflicts in YAML/JSON lockfiles = npm lockfile: regenerate (`npm install`) rather than hand-merging.

## 7. Definition of done (per task, repeated from `AGENTS.md`)

Implementation + tests + docs + `.env.example` + contract sync + green CI + PR (module owner reviews,
merge = squash into `develop`) + `tasks.md` status column updated.
