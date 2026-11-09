"""Repo-root pytest bootstrap (docs/testing-strategy.md layout).

Keeps package imports (backend.*, agent.*, integrations.*, voice.*) working when pytest is
invoked from either the repo root or its own subdirectories (rootdir = this file's directory).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
for p in (ROOT,):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))
