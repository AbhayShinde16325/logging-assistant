"""One-time Google Sheets tab setup (T-021) per docs/google-sheets-schema.md.

Creates any missing canonical tabs (Employees, Tasks, Activity_Log, Reminders, Command_Log)
with the byte-exact headers from `integrations/google_sheets/mapper.py`, and (optionally)
seeds the Employees rows the prototype expects.

Run (repo root): python scripts/setup_sheets.py
Requires real credentials in .env (GOOGLE_SHEETS_SPREADSHEET_ID + GOOGLE_APPLICATION_CREDENTIALS)
and the spreadsheet shared with the service-account email as Editor.
"""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root imports

from integrations.google_sheets.mapper import _HEADERS  # canonical source of truth
from backend.app.core.config import get_settings

SEED_EMPLOYEES = [
    ["EMP-001", "Rahul", "EMP-001@example.com", "Engineer"],
    ["EMP-002", "Priya", "EMP-002@example.com", "Designer"],
    ["EMP-003", "Aisha", "EMP-003@example.com", "Lead"],
]


def _service():
    from googleapiclient.discovery import build
    from google.oauth2.service_account import Credentials

    settings = get_settings()
    if not settings.sheets_configured:
        sys.exit("Missing GOOGLE_SHEETS_SPREADSHEET_ID / GOOGLE_APPLICATION_CREDENTIALS in .env")
    with open(settings.google_application_credentials, encoding="utf-8") as f:
        pass  # fail fast with a clean FileNotFoundError if the path is wrong
    creds = Credentials.from_service_account_file(
        settings.google_application_credentials,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=creds), settings.google_sheets_spreadsheet_id


def main() -> None:
    svc, spreadsheet_id = _service()

    existing = [s["properties"]["title"] for s in svc.spreadsheets()
                .get(spreadsheetId=spreadsheet_id).execute()["sheets"]]
    print(f"Existing tabs: {existing}")

    # 1) addSheet for every tab that does not exist yet
    requests = [
        {"addSheet": {"properties": {"title": tab}}}
        for tab in _HEADERS if tab not in existing
    ]
    if requests:
        svc.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": requests},
        ).execute()
        print(f"Created tabs: {[r['addSheet']['properties']['title'] for r in requests]}")
    else:
        print("All canonical tabs already exist — nothing to create.")

    # 2) write headers into every empty tab (never overwrite non-empty rows)
    for tab, header in _HEADERS.items():
        row = svc.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"{tab}!A1:Z1",
        ).execute().get("values", [])
        if row:
            print(f"{tab}: header present, skipped.")
            continue
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range=f"{tab}!A1",
            valueInputOption="RAW", body={"values": [header]},
        ).execute()
        print(f"{tab}: wrote header {header}")

    # 3) seed the three prototype employees (only if the tab is still empty)
    vals = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="Employees!A2:E10",
    ).execute().get("values", [])
    if not vals:
        svc.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range="Employees!A2",
            valueInputOption="RAW", body={"values": [
                row + ["2026-11-01T09:00:00.000Z"] for row in SEED_EMPLOYEES
            ]},
        ).execute()
        print("Employees: seeded Rahul (EMP-001), Priya (EMP-002), Aisha (EMP-003).")
    else:
        print(f"Employees: {len(vals)} row(s) already present — skipping seed.")

    print("Setup complete.")


if __name__ == "__main__":
    main()
