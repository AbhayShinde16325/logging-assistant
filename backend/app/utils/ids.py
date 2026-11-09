"""Shared ID + time helpers (see contracts/README.md for binding conventions).

IDs: `{prefix}-` + 8 lowercase hex. The LLM never generates IDs. Time: UTC ISO 8601 via an
injectable clock (AppClock) so tests and the reminder/reconciliation guard window are deterministic
(docs/testing-strategy.md "deterministic time" rule).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class Clock:
    """Injectable UTC clock. Tests replace `utcnow` (see FakeClock in tests)."""

    def utcnow(self) -> datetime:
        return datetime.now(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Serialize datetimes to contract format (ISO 8601 UTC, millisecond precision, Z)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso(value: str) -> datetime:
    """Parse contract timestamps; tolerate naive values (treated as UTC)."""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


DEFAULT_CLOCK = Clock()
