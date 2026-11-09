# Pull Request

## Modules affected
<!-- Check all that apply. Each module has one owner; flag them. -->
- [ ] `backend/` (Owner: Developer A)
- [ ] `agent/` (Owner: Developer A)
- [ ] `integrations/google_sheets/` (Owner: Developer B)
- [ ] `frontend/` (Owner: Developer C)
- [ ] `voice/` (Owner: Developer C)
- [ ] `contracts/` or other **shared files** (Owner: Developer A — coordination required)
- [ ] `docs/` / root files

## Task reference
<!-- Task ID from tasks.md, or issue # -->
-

## What & why
<!-- 2–6 sentences. Include any contract/decision the change depends on. -->

## Contract synchronization (required if schemas changed)
- [ ] `contracts/*.schema.json` updated
- [ ] Backend Pydantic schemas updated
- [ ] Frontend TypeScript interfaces updated
- [ ] `docs/api-contracts.md` updated
- N/A — no schema change

## Tests
- [ ] Unit tests added/updated and passing locally (`pytest` / `npm run test`)
- [ ] Contract tests updated (if API changed)
- [ ] Integration tests (only with explicit credentials, per docs/testing-strategy.md)
- N/A — no testable logic changed

## Test results
```
<paste command + result, or link the CI run>
```

## New dependencies
<!-- Name + one-line purpose, or "None". Undocumented dependencies block the merge. -->
- None

## Secrets & env vars
- [ ] No secrets committed; credentials kept out of the repo
- [ ] New env vars documented in `.env.example` and `backend/app/core/config.py`
- N/A

## Documentation
- Docs updated: <!-- files -->
  - N/A

## Ownership & conflict check
- [ ] I did not silently modify files owned by another developer (or I coordinated with them)
- [ ] Branch is up to date with `develop` (rebased)

## tasks.md status
- Updated task status to: `REVIEW` (for task ID(s): )
