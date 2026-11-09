# SKILL: Voice Processing

> **DE (skill-steward):** Developer C · Applies to: `voice/**` and browser voice-capture work.

## 1. Skill purpose

Implement the voice capability while keeping **transcription separate from orchestration**: capture,
transcription abstraction, transcription validation, and handing clean text to the chat workflow.

## 2. When the agent should use this skill

Tasks touching `voice/**` or the Web Speech capture in `frontend/**` (T-043, T-110, T-120).

## 3. Relevant directories and files

- Code: `voice/transcription.py`, `voice/schemas.py` (server-side abstraction)
- Code: `frontend/src/features/chat/*VoiceButton*` (browser capture, Web Speech API)
- Contract: `../docs/api-contracts.md` § Voice (including the honest `501` MVP state)
- Tests: `../tests/unit/voice/` (expected when DTO work lands)

## 4. Technology-specific implementation rules

- **Browser-first MVP**: capture + transcribe with Web Speech API (`SpeechRecognition` /
  `webkitSpeechRecognition`) in the browser; the user **edits/reviews** the text in the chat input
  before sending; no server upload in the default path.
- **Feature-detect**: if the API is unavailable (Firefox without config, etc.) the mic button is
  disabled with a tooltip/notice — no fake transcription, no silent fallback.
- **Abstraction stays real**: `voice/transcription.py` defines `Transcriber` + DTOs; until a
  server-side provider is chosen (future ADR), the endpoint documents `501
  NOT_IMPLEMENTED_NOT_WIREABLE`. Do not invent a magic provider or post pretend results.
- **Validation**: server-side DTO validates MIME (webm/wav/ogg), size ≤ 10 MB, non-empty
  transcription, language hint format; browser side validates recording length and recovers from
  permission-denied without crashing the chat UI.
- **Integration with chat**: transcribed text is a **string** handed to the same input the user
  types in; from there the identical `/chat` flow runs — no separate voice pipeline, no direct
  agent invocation from the UI.

## 5. Coding conventions

Pure protocol + dataclass DTOs (Pydantic v2); typed hooks for the Web Speech event lifecycle
(`start/end/error/result`); React state machine `idle → listening → transcribed(confirmable) → sent`.

## 6. Dependencies and interfaces

- No paid STT in the MVP. A server-side provider (e.g. whisper.cpp server or an Ollama-adjacent
  local solution) requires an ADR **before** implementation (cost/privacy/feasibility).
- The interface with the chat workflow is only text (via the input box, or the `/voice/transcribe`
  response when a provider exists).

## 7. Common mistakes to avoid

| Mistake | Correct |
|---|---|
| Streaming transcripts straight to `/chat` | Land in the editable input; user confirms content |
| Treating transcription as "good enough" without validation | Validate non-empty + trim + length caps before send |
| Mixing transcription into agent state | Text-in-message only; orchestration unchanged |
| Claiming server-side STT exists | Honest `501` until the ADR + provider are real |
| Vendor/proprietary JS SDK in the bundle | Not allowed (MVP cost constraint) |

## 8. Testing requirements

- DTO validation unit tests (mime/size/lang).
- Browser capture is best verified manually (Chrome demo): include in demo scenario notes
  (testing-strategy.md § demonstration) + graceful-degradation check (unsupported browser shows the
  disabled state).
- When a server provider lands: mock transport tests for timeout/error mapping to envelope codes.

## 9. Completion checklist

- [ ] Capture → edit → send flow works in Chrome; degraded state elsewhere
- [ ] Transcription never auto-sends and never touches task data directly
- [ ] Rules of `../docs/api-contracts.md` § Voice respected (no invented success responses)
- [ ] Unit tests for DTOs; manual demo notes recorded
