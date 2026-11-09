#!/usr/bin/env python3
"""Validate every JSON Schema in contracts/ is syntactically valid Draft 2020-12.

Use in CI (see .github/workflows/ci.yml) and run manually:
    python scripts/validate_contracts.py
"""
import json
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "contracts"

failures: list[str] = []
schemas = sorted(CONTRACTS.glob("*.schema.json"))
if not schemas:
    failures.append(f"No schema files found in {CONTRACTS}")

for path in schemas:
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(schema)
        print(f"OK      {path.name}")
    except Exception as exc:  # noqa: BLE001 — deliberate broad catch for CI reporting
        failures.append(f"INVALID {path.name}: {exc}")

if failures:
    for line in failures:
        print(line)
    sys.exit(1)

print(f"\nAll {len(schemas)} contract schemas are valid Draft 2020-12 JSON Schema.")
