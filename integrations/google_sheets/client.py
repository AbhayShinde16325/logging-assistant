"""Google Sheets v4 low-level client (task T-020, skill: google-sheets-integration).

Service-account auth only (GOOGLE_APPLICATION_CREDENTIALS path — never committed). Exposes ONLY
granular operations the repositories need; no business logic, no caching, no token logging.
Retries 429/503 with backoff (quota discipline). Unit tests use FakeGoogleSheetsClient —
this module must never require credentials unless marked integration (testing-strategy.md).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from backend.app.core.config import Settings
from backend.app.utils.errors import integration_error

logger = logging.getLogger("integrations.sheets")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_RETRY_STATUS = (429, 500, 503)
_MAX_RETRIES = 3
_BACKOFF_SECONDS = 1.5


class SheetsClientProto(Protocol):
    """Granular surface (docs/google-sheets-schema.md §1/§2): row values only — row numbers are
    transport detail and never identity."""

    def get_header(self, tab: str) -> list[str]: ...
    def get_rows(self, tab: str) -> list[list[str]]: ...
    def append_row(
        self, tab: str, row: list[str], *, skip_header: bool = True,
        header: list[str] | None = None,
    ) -> int: ...
    def update_row(self, tab: str, row_number: int, row: list[str]) -> None: ...
    def clear_row(self, tab: str, row_number: int) -> None: ...


class GoogleSheetsApiClient:
    """Service-account backed implementation (needs credentials; used in dev/prod)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.spreadsheet_id = settings.google_sheets_spreadsheet_id
        self._service = None

    def _get_service(self):
        if self._service is None:
            try:
                from google.oauth2.service_account import Credentials
                from googleapiclient.discovery import build
            except Exception as exc:  # pragma: no cover — import guard
                raise integration_error("Google Sheets client library not installed.") from exc
            if not self.settings.google_application_credentials:
                raise integration_error("GOOGLE_APPLICATION_CREDENTIALS not configured.")
            creds = Credentials.from_service_account_file(  # type: ignore[union-attr]
                self.settings.google_application_credentials, scopes=SCOPES,
            )
            self._service = build(
                "sheets", "v4", credentials=creds,
                cache_discovery=False, static_discovery=True,
            )
        return self._service

    # -- granular API ----------------------------------------------------------
    def get_header(self, tab: str) -> list[str]:
        result = self._call(lambda svc: svc.spreadsheets().values()
                            .get(spreadsheetId=self.spreadsheet_id, range=f"{tab}!A1:Z1").execute())
        rows = result.get("values", []) or []
        return rows[0] if rows else []

    def get_rows(self, tab: str) -> list[list[str]]:
        result = self._call(
            lambda svc: svc.spreadsheets().values()
            .get(spreadsheetId=self.spreadsheet_id, range=f"{tab}!A2:Z").execute()
        )
        return result.get("values", []) or []

    def append_row(
        self, tab: str, row: list[str], *, skip_header: bool = True,
        header: list[str] | None = None,
    ) -> int:
        # `header` mirrors the memory/fake-client contract: auto-create the header row
        # on an empty tab so repositories can pass the canonical mapper headers.
        if header is not None:
            first = self._call(
                lambda svc: svc.spreadsheets().values()
                .get(spreadsheetId=self.spreadsheet_id, range=f"{tab}!A1:Z1").execute()
            )
            if not first.get("values"):
                self._call(
                    lambda svc: svc.spreadsheets().values()
                    .update(
                        spreadsheetId=self.spreadsheet_id, range=f"{tab}!A1",
                        valueInputOption="USER_ENTERED", body={"values": [header]},
                    )
                    .execute()
                )
        result = self._call(
            lambda svc: svc.spreadsheets().values()
            .append(
                spreadsheetId=self.spreadsheet_id, range=f"{tab}!A:Z",
                valueInputOption="USER_ENTERED", insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            )
            .execute()
        )
        updates = result.get("updates", {})
        rng = updates.get("updatedRange", "")
        # returns the 1-based sheet row number appended to (transport detail only)
        try:
            import re

            m = re.search(r"([A-Z]+)(\d+):", rng.rsplit(":", 1)[-1] if ":" in rng else rng)
            return int(m.group(2)) if m else -1
        except Exception:  # noqa: BLE001 — best effort transport detail
            return -1

    def update_row(self, tab: str, row_number: int, row: list[str]) -> None:
        self._call(
            lambda svc: svc.spreadsheets().values()
            .update(
                spreadsheetId=self.spreadsheet_id, range=f"{tab}!A{row_number}:Z{row_number}",
                valueInputOption="USER_ENTERED", body={"values": [row]},
            )
            .execute()
        )

    def clear_row(self, tab: str, row_number: int) -> None:
        self._call(
            lambda svc: svc.spreadsheets().values()
            .clear(spreadsheetId=self.spreadsheet_id, range=f"{tab}!A{row_number}:Z{row_number}")
            .execute()
        )

    # -- retry / error mapping ------------------------------------------------
    def _call(self, fn, *, retries: int = _MAX_RETRIES):
        for attempt in range(retries):
            try:
                return fn(self._get_service())
            except Exception as exc:  # noqa: BLE001 — typed mapping below
                status = getattr(getattr(exc, "resp", None), "status", None) or \
                    getattr(getattr(getattr(exc, "result", None), "status", None), "status", None)
                if status in _RETRY_STATUS and attempt < retries - 1:
                    wait = _BACKOFF_SECONDS * (2 ** attempt)
                    logger.warning("Sheets API retry %s/3 after %ss: %s", attempt + 1, wait, exc)
                    time.sleep(wait)
                    continue
                logger.exception("Sheets API call failed")
                raise integration_error(
                    f"Google Sheets request failed ({getattr(exc, '__class__', type(exc)).__name__}). "
                    "The action was not saved.",
                    {"spreadsheet_configured": bool(self.spreadsheet_id)},
                ) from exc
        raise integration_error("Google Sheets request failed after retries.")  # pragma: no cover
