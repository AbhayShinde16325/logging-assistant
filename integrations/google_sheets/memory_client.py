"""In-memory sheets client — DEV/TEST fallback ONLY (never a data-plane implementation).

Implements the client protocol (get_header/get_rows/append_row/update_row/clear_row) over a dict
of tabs so the Sheets repositories can run with zero credentials in tests and offline dev
(ADR-002 explicitly keeps Sheets the MVP source of truth — production always uses the real client).
Data layout mirrors the API's row/transport contract so mapper/repositories/reconciliation tests
exercise REAL Sheets code paths against fakes (docs/testing-strategy.md).
"""

from __future__ import annotations

import re
from typing import Any

from backend.app.utils.errors import integration_error


class MemorySheetsClient:
    """Simple get/set/clear per google-sheets-schema.md tabs.

    Row numbering is 1-based: get_rows() returns rows BELOW the header row; row_number in
    update_row/clear_row counts the header as row 1 (matches the real API behavior).
    """

    def __init__(self, tabs: dict[str, list[list[str]]] | None = None) -> None:
        self.tabs: dict[str, list[list[str]]] = tabs if tabs is not None else {}
        self.next_row: dict[str, int] = {}
        # Track app-created rows to enable self-write guard verification (T-100).
        self._last_write_row: dict[str, tuple[int, Any]] = {}

    def _ensure(self, tab: str, header: list[str] | None = None) -> list[list[str]]:
        if tab not in self.tabs:
            self.tabs[tab] = [list(header)] if header else [[]]
        return self.tabs[tab]

    # -- protocol ------------------------------------------------------------
    def get_header(self, tab: str, header: list[str] | None = None) -> list[str]:
        if tab in self.tabs and self.tabs[tab]:
            return list(self.tabs[tab][0])
        return list(header or [])

    def read_header_cell(self, tab: str) -> list[str]:
        return self.get_header(tab)

    def get_rows(self, tab: str, header: list[str] | None = None) -> list[list[str]]:
        return [list(row) for row in self._ensure(tab, header)[1:]]

    @staticmethod
    def _parse_range(range_str: str) -> str:
        m = re.match(r"^([A-Za-z0-9_]+)!", range_str)
        if m:
            return m.group(1)
        return range_str

    def append_row(self, tab: str, row: list[str], *, skip_header: bool = True,
                   header: list[str] | None = None) -> int:
        rows = self._ensure(tab, header)
        rows.append(list(row))
        self.next_row[tab] = len(rows)
        return len(rows)  # 1-based sheet row (header = row 1)

    def update_row(self, tab: str, row_number: int, row: list[str]) -> None:
        rows = self._ensure(tab)
        if row_number < 1 or row_number > len(rows):
            raise integration_error(f"Row {row_number} out of range for tab {tab}.", {})
        rows[row_number - 1] = list(row)

    def clear_row(self, tab: str, row_number: int) -> None:
        rows = self._ensure(tab)
        if row_number < 1 or row_number > len(rows):
            return
        rows[row_number - 1] = []

    def count_rows(self, tab: str) -> int:
        return sum(1 for row in self._ensure(tab)[1:] if any(str(cell).strip() for cell in row))

    # -- test simulation helpers (FakeGoogleSheetsClient in tests builds on these) --
    def set_row(self, tab: str, row_number: int, row: list[str]) -> None:
        """Simulate a MANUAL edit directly in the sheet (bypasses repositories)."""
        rows = self._ensure(tab)
        while len(rows) < row_number:
            rows.append([])
        rows[row_number - 1] = list(row)

    def all_rows(self, tab: str) -> list[list[str]]:
        return [list(row) for row in self._ensure(tab)]
