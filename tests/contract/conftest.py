"""Contract test bootstrap (docs/testing-strategy.md contract layer).

Builds the FastAPI app from a test container (Sheets repositories + fake client) so every
documented route, status code and error envelope is validated without external services.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app
from tests.unit.conftest import FakeClock, SEED_TIME  # noqa: F401


@pytest.fixture()
def fake_clock(seed_time):
    return FakeClock(seed_time)


@pytest.fixture()
def client(sheets_container) -> TestClient:
    app = create_app(container=sheets_container)
    return TestClient(app)
