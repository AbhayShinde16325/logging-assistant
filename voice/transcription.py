"""Transcription abstraction (task T-043) — the only place a server-side provider would plug in.

docs/api-contracts.md honesty note: the MVP does voice in the browser (Web Speech API). No
server-side provider is wired; whenever `Transcriber` implementations land, they must go through an
ADR (voice/AGENTS.md). The `StubServerTranscribe` returns None and the route maps it to 501.
"""

from __future__ import annotations

from typing import Protocol

from voice.schemas import AudioUploadMeta, TranscriptionResult, validate_upload

__all__ = ["AudioUploadMeta", "StubServerTranscribe", "Transcriber", "TranscriptionResult", "validate_upload"]


class Transcriber(Protocol):
    """Server-side transcription backends implement this. MVP keeps our local spot free."""

    name: str

    def transcribe(self, audio: bytes, meta: "AudioUploadMeta") -> "TranscriptionResult | None": ...

    def is_available(self) -> bool: ...


class StubServerTranscribe:
    """Draft provider — always None so callers surface a 501 NOT_IMPLEMENTED_NOT_WIREABLE."""

    name = "stub"

    def transcribe(
        self, audio: bytes, meta: "AudioUploadMeta",
    ) -> "TranscriptionResult | None":
        return None

    def is_available(self) -> bool:
        return True
