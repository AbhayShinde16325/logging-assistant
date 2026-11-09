# voice/ — AGENTS.md

Owner: **Developer C**. Refines the root [`../AGENTS.md`](../AGENTS.md) without contradicting it.

## Module purpose

A **pluggable transcription abstraction**: audio DTOs, validation, and provider backends that the
backend wires into `POST /api/v1/voice/transcribe`. In the MVP the real transcription happens in
the **browser** (Web Speech API) inside `frontend/`; this module keeps the abstraction honest so a
server-side provider can be added later.

## Read before coding

1. Root [`../AGENTS.md`](../AGENTS.md)
2. [`../skills/voice-processing/SKILL.md`](../skills/voice-processing/SKILL.md)
3. [`../docs/api-contracts.md`](../docs/api-contracts.md) § Voice
4. `../docs/architecture.md` §2 (module boundary: transcription ≠ orchestration)

## Layout

```text
voice/
├── transcription.py   ← Transcriber protocol + provider selection (env) + MVP stub (501 path)
└── schemas.py         ← AudioUpload / TranscriptionResult DTOs (frames of the API contract)
```

## Hard module rules

- Transcription output is **text only**; this module never calls the agent, backend services, or
  Google Sheets (transcription is separate from orchestration — workflow doc §1).
- Provider selection is env/config-driven; adding a provider = new class + config, no API change.
- Validate uploads strictly (size ≤ 10 MB, supported MIME types) and raise typed validation errors
  that routes map to the error envelope (`422 INVALID_AUDIO` etc. per api-contracts.md).
- MVP honesty: until a server-side provider is implemented, the route returns `501
  NOT_IMPLEMENTED_NOT_WIREABLE` — do **not** fake a provider or pretend it works.
- No client-side (browser) code lives here; Web Speech usage belongs to `../frontend/` (T-110).

## Conventions

- Full type hints; DTOs are Pydantic; pure functions where possible; unit tests without network IO
  (fixtures in `../tests/unit/`).
