"""Voice DTOs (task T-043) — mirror docs/api-contracts.md § Voice.

Validation here matches the contract: multipart upload ≤ 10 MB, webm/wav/ogg only, non-empty
transcription. These DTOs are shared by the (future) server-side provider and route tests — the
browser Web Speech path does NOT use this module.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AudioMime = Literal["audio/webm", "audio/wav", "audio/x-wav", "audio/ogg"]
MAX_AUDIO_BYTES = 10 * 1024 * 1024
AUDIO_SUFFIXES: tuple[str, ...] = (".webm", ".wav", ".ogg")


class AudioUploadMeta(BaseModel):
    """Metadata extracted from a multipart UploadFile before the provider call."""

    filename: str
    content_type: str | None = None
    size_bytes: int
    language: str = Field(default="en", max_length=10)


class TranscriptionResult(BaseModel):
    transcription: str = Field(min_length=0, max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    provider: str


def validate_upload(filename: str | None, size_bytes: int) -> AudioUploadMeta:
    """Raise a contract-shaped summary; routes map to VALIDATION_ERROR (422)."""
    name = (filename or "").lower()
    if not name:
        raise ValueError("Filename is required.")
    if not name.endswith(AUDIO_SUFFIXES):
        raise ValueError(
            f"Unsupported upload type '{name}'. Allowed mime: webm/wav/ogg."
        )
    if size_bytes <= 0:
        raise ValueError("Empty audio upload.")
    if size_bytes > MAX_AUDIO_BYTES:
        raise ValueError("Audio must be 10MB or less.")
    return AudioUploadMeta(
        filename=name,
        content_type=_guess_mime(name),
        size_bytes=size_bytes,
    )


def _guess_mime(name: str) -> str:
    if name.endswith(".webm"):
        return "audio/webm"
    if name.endswith(".wav"):
        return "audio/wav"
    return "audio/ogg"
