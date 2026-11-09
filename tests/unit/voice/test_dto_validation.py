"""Voice DTO validation (docs/testing-strategy.md "voice transcription handling")."""

from __future__ import annotations

import pytest

from voice.schemas import TranscriptionResult, validate_upload


def test_accepts_webm_upload() -> None:
    meta = validate_upload("chat.webm", 2048)
    assert meta.language == "en" and meta.content_type == "audio/webm"


def test_rejects_bad_extension() -> None:
    with pytest.raises(ValueError):
        validate_upload("voice.mp3", 1024)


def test_rejects_empty_audio() -> None:
    with pytest.raises(ValueError):
        validate_upload("voice.wav", 0)


def test_rejects_oversize_audio() -> None:
    with pytest.raises(ValueError):
        validate_upload("voice.wav", 11 * 1024 * 1024)


def test_transcription_bounds() -> None:
    with pytest.raises(Exception):
        TranscriptionResult(transcription="", confidence="not-a-float", provider="web")
