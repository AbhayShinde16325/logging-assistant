"""Transcription abstraction (scaffold — task T-043, wire-up by A in T-120).

Defines the Transcriber provider protocol. MVP: browser (Web Speech API) handles capture in
frontend/; the server route exposes the 501 contract per docs/api-contracts.md § Voice until a
server-side provider is implemented under an ADR.
"""

from __future__ import annotations
