"""Google Sheets low-level client (scaffold — task T-020).

Service-account authentication + thin wrappers over the Sheets v4 API used by the repositories:
- authorize: service-account from GOOGLE_APPLICATION_CREDENTIALS path
- get_rows / append_row / update_row / clear_row / get_header

Unit-tested with a fake transport (no credentials in unit runs). See module AGENTS.md.
"""

from __future__ import annotations


class SheetsClientProtocol:
    """Documentation-only protocol sketch (see google-sheets-schema.md for tab/column contract)."""
