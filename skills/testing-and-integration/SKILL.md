# SKILL: Testing and Integration

> **DE (skill-steward):** Developer A (strategy) · Applies to: **everyone** (each owner tests their module).

## 1. Skill purpose

Enable the writing of consistent, fast, meaningful tests: unit, contract, and opt-in integration —
with mocking discipline (LLM, Google Sheets) and cross-module validation. This skill is required
reading before any PR whose Definition of Done includes "tests pass".

## 2. When the agent should use this skill

Before writing any test, any fixture/fake, or wiring a new external dependency into the suite.

## 3. Relevant directories and files

- Tests: `tests/unit/`, `tests/contract/`, `tests/integration/`; tooling `tests/requirements.txt`
- Strategy (authoritative): `../docs/testing-strategy.md`
- Fakes: `FakeGoogleSheetsClient` (unit/, T-030), `MockModelProvider` (unit/fixtures), Fake ports
  (`Fake*Repository`) next to `backend/app/services/ports.py` (T-012)
- Validators: `scripts/validate_contracts.py`; CI: `.github/workflows/ci.yml`

## 4. Implementation rules

- **Three layers, clear boundaries:**
  - `unit/*` — pure logic with fakes; no network; milliseconds-fast; naming:
    `test_<unit>_<behavior>.py` (pytest), `*.test.ts(x)` (Vitest).
  - `contract/*` — FastAPI `TestClient` with **mocked ports**: every documented endpoint, the
    documented status codes, the error envelope, and jsonschema validation of schema examples
    (`contracts/`). Also `test_full_flow.py`: chat → propose → confirm → (fake) repository effects
    → activity rows — the mocked end-to-end run.
  - `integration/*` — **requires real external services**; skipped unless
    `GOOGLE_SHEET_TESTS_ENABLED=1`; marked `@pytest.mark.integration`; disposable spreadsheet only.
- **Mock discipline:** one fake per interface (never per test); fixture transcripts for LLM outputs
  live in `agent/app/prompts/`-adjacent fixtures and are updated together with prompt PRs; fakes
  mimic *documented* behavior only (no invented API).
- **Contract fixtures:** sample valid/invalid payloads per schema live in
  `tests/contract/fixtures/`; backend emits a sample payload for each schema and it must validate
  against the JSON Schema file — that's the drift alarm.
- **Deterministic time:** inject a clock/`now` provider; never `datetime.now()` scattered — reminder
  expiry (24h) and the reconciliation guard window are constant-injected tests.
- **Idempotency checks are contract tests:** double-confirm, double-reject, confirm-after-expiry
  behaviors are all explicitly asserted (they are real-world crash scenarios at this stage).

## 5. Closing the loop on cross-module validation

- Fake-client-driven repository tests (B) + route/contract tests (A) + component fixture tests (C)
  all reference **the same schema files** — this is how the three implementations stay synchronized,
  and why contract-test failures fail the build for everyone, regardless of owner.
- Scenario scripts (manual demo, Milestone 5): every code path from docs/testing-strategy.md
  § demonstration is asserted (as far as automation allows) before the manual handoff.

## 6. Dependencies and interfaces

- pytest 8, pytest-asyncio, jsonschema, httpx already in `tests/requirements.txt` — new dev deps
  require a PR justification like runtime deps.
- New ports require: fake implementation + one unit test using it, in the same PR (ports owner: A).

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Copy-pasting a fake from another test file | Reuse the canonical fake; fix the fake not the copy |
| Unit tests hitting network or Ollama/Sheets | Only `tests/integration/` (opt-in) may reach out |
| Asserting on internal call order | Assert behavior/results (ports invoked with expected args), not implementation |
| Random IDs/dates in assertions | Inject fixed clock / fixed seed; assert exact IDs where feasible |
| Marking flaky tests with sleeps | Use deterministic injection of time/resource; else quarantine until fixed |
| Integration tests in CI without env flag | They must skip cleanly; CI runs with `GOOGLE_SHEET_TESTS_ENABLED=0` |

## 8. Testing requirements (for tests themselves)

- Run `pytest -q` (all unit + contract) locally before PRs; keep suite < ~2 minutes.
- Frontend: `npm run test` (Vitest) for component tests; CI gates stay green.
- ADR-for-all: **every PR in this repo updates or adds at least one test OR explicitly declares in
  the PR template why no test is needed** ("N/A — no testable logic changed" is respected by
  reviewers, but it must *actually* hold).

## 9. Completion checklist

- [ ] New/changed logic covered in the right layer (unit/contract/integration) per docs/testing-strategy.md
- [ ] Single canonical fakes used; no network in unit/contract; tests are deterministic
- [ ] `scripts/validate_contracts.py` green after any contracts change
- [ ] PR includes test output; CI green; no skipped-but-relevant tests unflagged
