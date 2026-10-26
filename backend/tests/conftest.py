"""Shared test fixtures."""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.data_service import WindData
from app.elexon_client import RawRow
from app.main import app
from app.routes import get_wind_data
from app.schemas import ActualRow, DatasetSummary, ForecastRow, Snapshot

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


def _utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=UTC)


def build_test_snapshot(forecasts: list[ForecastRow], actuals: list[ActualRow]) -> Snapshot:
    """Wrap rows in a snapshot with a plausible audit; 1488 is the half-hours in the window."""
    summary_forecasts = DatasetSummary(
        rows_fetched=len(forecasts), rows_kept=len(forecasts), rows_dropped={}
    )
    summary_actuals = DatasetSummary(
        rows_fetched=len(actuals), rows_kept=len(actuals), rows_dropped={}
    )
    return Snapshot(
        first_delivery_day=date(2026, 1, 2),
        last_delivery_day=date(2026, 2, 1),
        forecast_summary=summary_forecasts,
        actual_summary=summary_actuals,
        missing_actual_half_hours=1488 - len(actuals),
        forecasts=forecasts,
        actuals=actuals,
    )


@pytest.fixture
def make_wind_data() -> Callable[[list[ForecastRow], list[ActualRow]], WindData]:
    """Return a function that builds WindData from hand-written rows."""

    def make(forecasts: list[ForecastRow], actuals: list[ActualRow]) -> WindData:
        return WindData(build_test_snapshot(forecasts, actuals))

    return make


@pytest.fixture
def wind_snapshot() -> Snapshot:
    """Two delivery days (2 and 3 Jan), hours 00 and 01 only, with values that are easy to check.

    Every target hour has a 07:30 forecast (the one used at the 09:00 cutoff) and a 09:30 forecast
    (too late for it). Errors (actual - forecast) at the 09:00 cutoff:
    2 Jan: -100, +100, +200, -200.  3 Jan: +300, -300, -100, +300.
    """
    forecast_table = [
        (_utc(1, 7, 30), _utc(2, 0), 1000.0),
        (_utc(1, 9, 30), _utc(2, 0), 1100.0),
        (_utc(1, 7, 30), _utc(2, 1), 2000.0),
        (_utc(1, 9, 30), _utc(2, 1), 2100.0),
        (_utc(2, 7, 30), _utc(3, 0), 3000.0),
        (_utc(2, 9, 30), _utc(3, 0), 3100.0),
        (_utc(2, 7, 30), _utc(3, 1), 4000.0),
        (_utc(2, 9, 30), _utc(3, 1), 4100.0),
    ]
    actual_table = [
        (_utc(2, 0, 0), 900.0),
        (_utc(2, 0, 30), 1100.0),
        (_utc(2, 1, 0), 2200.0),
        (_utc(2, 1, 30), 1800.0),
        (_utc(3, 0, 0), 3300.0),
        (_utc(3, 0, 30), 2700.0),
        (_utc(3, 1, 0), 3900.0),
        (_utc(3, 1, 30), 4300.0),
    ]
    forecasts = [
        ForecastRow(publish_time_utc=publish, start_time_utc=start, generation_mw=mw)
        for publish, start, mw in forecast_table
    ]
    actuals = [ActualRow(start_time_utc=start, generation_mw=mw) for start, mw in actual_table]
    return build_test_snapshot(forecasts, actuals)


@pytest.fixture
def wind_data(wind_snapshot: Snapshot) -> WindData:
    return WindData(wind_snapshot)


@pytest.fixture
def api_client(wind_data: WindData) -> Iterator[TestClient]:
    """Test client whose data is the small fixture snapshot, not the committed file."""
    app.dependency_overrides[get_wind_data] = lambda: wind_data
    yield TestClient(app)
    app.dependency_overrides.clear()
