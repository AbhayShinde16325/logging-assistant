"""Manual-edit reconciliation (scaffold — task T-100).

Poll workers per docs/google-sheets-schema.md §3: snapshot compare, MANUAL_SHEET_EDIT detection,
self-write guard window, deterministic conflict rule (manual edit wins the row's content), and the
MANUAL_SHEET_EDIT activity entries.
"""

from __future__ import annotations
