"""Shared test fixtures."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.elexon_client import RawRow
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client() -> TestClient:
    """Return a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make retry backoff instant so failure tests run fast."""
    monkeypatch.setattr("app.elexon_client.ELEXON_RETRY_BACKOFF_SECONDS", 0.0)


def _load_rows(file_name: str) -> list[RawRow]:
    rows: list[RawRow] = json.loads((FIXTURES_DIR / file_name).read_text(encoding="utf-8"))
    return rows


@pytest.fixture
def windfor_rows() -> list[RawRow]:
    """Nine raw WINDFOR rows: 4 valid, 1 duplicate, 1 null, 2 outside window, 1 negative horizon."""
    return _load_rows("windfor_sample.json")


@pytest.fixture
def fuelhh_rows() -> list[RawRow]:
    """Seven raw FUELHH rows: 3 valid WIND, 1 CCGT, 1 duplicate, 1 outside window, 1 null."""
    return _load_rows("fuelhh_sample.json")
