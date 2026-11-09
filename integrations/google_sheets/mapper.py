"""Row <=> domain-object mapping (scaffold — task T-022).

Implements docs/google-sheets-schema.md §2 rules: empty cells -> null, unparseable values ->
'degraded' flags, exact column order per tab header, timestamps UTC ISO-8601.
"""

from __future__ import annotations
