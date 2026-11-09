"""Model-provider abstraction (task T-014) — the ONLY place that touches an LLM.

Protocol: BaseModelProvider. Implementations:
- OllamaProvider — plain HTTP against OLLAMA_BASE_URL (no SDK), json format, retry once.
- MockModelProvider — canned structured JSON keyed by the prompt's "TAG: <name>" marker (tests).
Business logic/classification/extraction NEVER imports Ollama or any SDK directly.
Provider selection = config (MODEL_PROVIDER/OLLAMA_MODEL), not code edits.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

import httpx

from backend.app.core.config import Settings

PROMPT_TIMEOUT_FALLBACK = 60.0

_RETRY_GUIDANCE = (
    "Your previous reply could not be parsed as JSON. Reply with ONLY valid JSON "
    "matching the requested schema. No prose, no code fences."
)


class ModelProvider(Protocol):
    name: str

    def complete_json(self, system_prompt: str, user_prompt: str,
                      timeout: float | None = None) -> str | None: ...

    def is_available(self) -> bool: ...


class ProviderUnavailableError(RuntimeError):
    pass


class BadRequestToModelLLMError(Exception):
    pass


def _tag(system_prompt: str) -> str:
    """Extract the TAG: marker (prompts embed 'TAG: <NAME>' in the system prompt)."""
    for line in system_prompt.splitlines():
        if line.strip().startswith("TAG:"):
            return line.strip()[4:].strip().split()[0]
    return ""


class OllamaProvider:
    """Local Ollama HTTP inference (httpx). Retries once with corrective guidance on bad output."""

    name = "ollama"
    _availability: bool | None = None

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete_json(
        self, system_prompt: str, user_prompt: str, timeout: float | None = None,
    ) -> str | None:
        timeout = timeout or self.settings.llm_timeout_seconds or PROMPT_TIMEOUT_FALLBACK
        payload = {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        last_err: Exception | None = None
        for guidance in ("", _RETRY_GUIDANCE):
            system_content = system_prompt if not guidance else f"{system_prompt}\n\n{guidance}"
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_prompt},
            ]
            try:
                resp = httpx.post(
                    url, json=payload | {"messages": messages}, timeout=timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if content and _valid_json_text(content):
                    self._availability = True
                    return content
                last_err = ValueError("model output not valid JSON")
            except httpx.ConnectError:
                self._availability = False
                raise ProviderUnavailableError("Ollama is not reachable") from None
            except Exception as err:  # noqa: BLE001 — wrapper for retry/reporting
                last_err = err
        self._availability = True
        raise RuntimeError(f"Ollama returned unparseable output: {last_err}")

    def is_available(self) -> bool:
        if self._availability is not None:
            return self._availability
        try:
            resp = httpx.get(
                f"{self.settings.ollama_base_url.rstrip('/')}/api/tags", timeout=2.0,
            )
            self._availability = resp.status_code == 200
        except Exception:  # noqa: BLE001 — availability probe
            self._availability = False
        return self._availability


def _valid_json_text(text: str) -> bool:
    """Never assume model output is valid JSON (root AGENTS.md §4)."""
    try:
        json.loads(text)
    except Exception:  # noqa: BLE001 — validation only
        return False
    return True


class MockModelProvider:
    """Canned structured JSON per TAG for tests (docs/testing-strategy.md)."""

    name = "mock"

    def __init__(self, canned: dict[str, str] | None = None) -> None:
        self.canned = canned or {}

    def complete_json(
        self, system_prompt: str, user_prompt: str, timeout: float | None = None,
    ) -> str | None:
        return self.canned.get(_tag(system_prompt))

    def is_available(self) -> bool:
        return False
