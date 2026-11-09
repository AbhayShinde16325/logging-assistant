# tests/ — AGENTS.md (overlay; root AGENTS.md applies everywhere)

Shared test suite owned per module (contract tests by A; module-specific unit tests land in each
owner's PRs). Strategy: [`../docs/testing-strategy.md`](../docs/testing-strategy.md); skill:
[`../skills/testing-and-integration/SKILL.md`](../skills/testing-and-integration/SKILL.md).

## Layout

```text
tests/
├── unit/         fast tests; no network; FakeGoogleSheetsClient, MockModelProvider, Fake* ports
├── contract/     FastAPI TestClient + jsonschema: every documented route/status/error envelope
├── integration/  REAL Google Sheets + optional REAL Ollama — opt-in via GOOGLE_SHEET_TESTS_ENABLED=1
└── requirements.txt   pytest, pytest-asyncio, httpx, ruff, mypy (install with backend/requirements.txt)
```

## Rules

- Unit/contract suites never require credentials, Ollama, or a spreadsheet — CI runs them.
- Integration tests are marked `@pytest.mark.integration` and skipped by default; they use a
  **disposable test spreadsheet**, never developer data.
- The fakes live once (`FakeGoogleSheetsClient` in `unit/`, T-030) and are shared — never fork fakes.
- If an implementation change breaks a fixture-based extraction test, update fixture **and** prompt
  together in same PR (testing-strategy.md "regenerate fixtures" rule).