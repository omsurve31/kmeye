"""Tests for the /api endpoints: status codes, response shape, known values and bad input.

Most tests use the small hand-checkable snapshot from conftest.py (see test_data_service.py for the
arithmetic). The last group runs against the committed snapshot to prove the real wiring.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import MAX_CACHED_CUTOFFS
from app.data_service import WindData
from app.errors import SnapshotError
from app.main import app
from app.routes import get_wind_data, load_wind_data
from app.schemas import Snapshot
from app.snapshot import write_snapshot

ALL_PATHS = {
    "/api/health",
    "/api/meta",
    "/api/decision",
    "/api/accuracy/summary",
    "/api/accuracy/series",
    "/api/accuracy/by-hour",
    "/api/accuracy/by-day",
    "/api/accuracy/by-horizon",
    "/api/accuracy/distribution",
}
BAD_CUTOFFS = [
    "9:00",
    "24:00",
    "09:60",
    "09:00:00",
    "abcde",
    "09:00%0A",
    "%27%3B%20DROP%20TABLE%20x%3B--",
    "9" * 1000,
    "",
]
RANGE_ENDPOINTS = [
    "/api/accuracy/summary",
    "/api/accuracy/series",
    "/api/accuracy/by-hour",
    "/api/accuracy/by-day",
    "/api/accuracy/by-horizon",
    "/api/accuracy/distribution",
]


@pytest.fixture
def fresh_loader_cache() -> Iterator[None]:
    load_wind_data.cache_clear()
    yield
    load_wind_data.cache_clear()


def test_openapi_documents_every_endpoint(client: TestClient) -> None:
    paths = set(client.get("/openapi.json").json()["paths"])

    assert paths == ALL_PATHS


def test_meta_returns_window_assumptions_and_audit(api_client: TestClient) -> None:
    response = api_client.get("/api/meta")

    body = response.json()
    assert response.status_code == 200
    assert body["first_delivery_day"] == "2026-01-02"
    assert body["last_delivery_day"] == "2026-02-01"
    assert body["default_cutoff_time_uk"] == "09:00"
    assert body["timezone"] == "Europe/London"
    assert body["missing_actual_half_hours"] == 1480
    assert body["forecast_summary"]["rows_kept"] == 8


def test_decision_returns_forecast_publish_time_band_and_actual(api_client: TestClient) -> None:
    response = api_client.get("/api/decision?day=2026-01-02")

    body = response.json()
    first_point = body["points"][0]
    assert response.status_code == 200
    assert body["cutoff_utc"] == "2026-01-01T09:00:00Z"
    assert body["forecast_publish_times_utc"] == ["2026-01-01T07:30:00Z"]
    assert len(body["points"]) == 4
    assert first_point["start_time_utc"] == "2026-01-02T00:00:00Z"
    assert first_point["forecast_publish_time_utc"] == "2026-01-01T07:30:00Z"
    assert first_point["forecast_mw"] == 1000.0
    assert first_point["band_low_mw"] == pytest.approx(760.0)
    assert first_point["band_high_mw"] == pytest.approx(1240.0)
    assert first_point["actual_mw"] == 900.0
    assert body["expected_total_mwh"] == pytest.approx(3000.0)


def test_decision_cutoff_parameter_changes_the_forecast_used(api_client: TestClient) -> None:
    response = api_client.get("/api/decision?day=2026-01-02&cutoff=10:00")

    body = response.json()
    assert response.status_code == 200
    assert body["cutoff_time_uk"] == "10:00"
    assert body["forecast_publish_times_utc"] == ["2026-01-01T09:30:00Z"]


@pytest.mark.parametrize(
    "query",
    [
        "",
        "day=",
        "day=not-a-date",
        "day=2026-13-01",
        "day=2026-01-01",
        "day=2026-02-02",
        "day=2025-12-31",
        "day=" + "2" * 5000,
    ],
)
def test_decision_invalid_day_returns_422(api_client: TestClient, query: str) -> None:
    response = api_client.get(f"/api/decision?{query}")

    assert response.status_code == 422
    assert "detail" in response.json()


def test_decision_day_outside_window_message_names_the_allowed_days(
    api_client: TestClient,
) -> None:
    detail = api_client.get("/api/decision?day=2026-03-01").json()["detail"]

    assert "2026-01-02" in detail
    assert "2026-02-01" in detail


@pytest.mark.parametrize("cutoff", BAD_CUTOFFS)
def test_decision_malformed_cutoff_returns_422(api_client: TestClient, cutoff: str) -> None:
    response = api_client.get(f"/api/decision?day=2026-01-02&cutoff={cutoff}")

    assert response.status_code == 422


def test_decision_first_delivery_day_is_accepted(api_client: TestClient) -> None:
    assert api_client.get("/api/decision?day=2026-01-02").status_code == 200


def test_decision_last_delivery_day_is_accepted_but_has_no_data_in_the_fixture(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/decision?day=2026-02-01")

    assert response.status_code == 404
    assert "2026-02-01" in response.json()["detail"]


def test_accuracy_summary_defaults_to_whole_window_and_default_cutoff(
    api_client: TestClient,
) -> None:
    response = api_client.get("/api/accuracy/summary")

    body = response.json()
    assert response.status_code == 200
    assert (body["first_day"], body["last_day"], body["cutoff_time_uk"]) == (
        "2026-01-02",
        "2026-02-01",
        "09:00",
    )
    assert body["summary"]["sample_count"] == 8
    assert body["summary"]["mae_mw"] == pytest.approx(200.0)
    assert body["summary"]["bias_mw"] == pytest.approx(25.0)
    assert body["summary"]["abs_error_p90_mw"] == pytest.approx(300.0)


def test_accuracy_summary_from_and_to_limit_the_days(api_client: TestClient) -> None:
    response = api_client.get("/api/accuracy/summary?from=2026-01-02&to=2026-01-02")

    summary = response.json()["summary"]
    assert response.status_code == 200
    assert summary["sample_count"] == 4
    assert summary["mae_mw"] == pytest.approx(150.0)


def test_accuracy_series_lists_every_half_hour_with_its_error(api_client: TestClient) -> None:
    response = api_client.get("/api/accuracy/series")

    points = response.json()["points"]
    assert response.status_code == 200
    assert len(points) == 8
    assert points[0] == {
        "start_time_utc": "2026-01-02T00:00:00Z",
        "forecast_mw": 1000.0,
        "actual_mw": 900.0,
        "error_mw": -100.0,
    }


def test_accuracy_by_hour_returns_one_entry_per_hour(api_client: TestClient) -> None:
    hours = api_client.get("/api/accuracy/by-hour").json()["hours"]

    assert [entry["hour_of_day"] for entry in hours] == [0, 1]
    assert hours[0]["summary"]["mae_mw"] == pytest.approx(200.0)


def test_accuracy_by_day_returns_one_entry_per_delivery_day(api_client: TestClient) -> None:
    days = api_client.get("/api/accuracy/by-day").json()["days"]

    assert [entry["delivery_day"] for entry in days] == ["2026-01-02", "2026-01-03"]
    assert days[1]["summary"]["mae_mw"] == pytest.approx(250.0)


def test_accuracy_by_horizon_uses_all_forecasts_in_six_hour_bins(api_client: TestClient) -> None:
    body = api_client.get("/api/accuracy/by-horizon").json()

    assert body["bin_hours"] == 6.0
    assert len(body["horizons"]) == 1
    assert body["horizons"][0]["horizon_start_hours"] == 12.0
    assert body["horizons"][0]["summary"]["sample_count"] == 16


def test_accuracy_distribution_returns_histogram_bins(api_client: TestClient) -> None:
    body = api_client.get("/api/accuracy/distribution").json()

    assert body["bin_width_mw"] == 500.0
    assert [(b["bin_start_mw"], b["count"]) for b in body["bins"]] == [(-500.0, 4), (0.0, 4)]


@pytest.mark.parametrize("endpoint", RANGE_ENDPOINTS)
@pytest.mark.parametrize(
    "query",
    [
        "from=2026-01-03&to=2026-01-02",
        "from=2026-01-01",
        "to=2026-02-02",
        "from=not-a-date",
        "to=2026-99-99",
        "from=" + "9" * 5000,
    ],
)
def test_accuracy_invalid_day_range_returns_422(
    api_client: TestClient, endpoint: str, query: str
) -> None:
    response = api_client.get(f"{endpoint}?{query}")

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize("cutoff", BAD_CUTOFFS)
def test_accuracy_malformed_cutoff_returns_422(api_client: TestClient, cutoff: str) -> None:
    response = api_client.get(f"/api/accuracy/summary?cutoff={cutoff}")

    assert response.status_code == 422


@pytest.mark.parametrize("endpoint", RANGE_ENDPOINTS)
def test_accuracy_range_without_data_returns_404(api_client: TestClient, endpoint: str) -> None:
    response = api_client.get(f"{endpoint}?from=2026-01-10&to=2026-01-10")

    assert response.status_code == 404
    assert "selected days" in response.json()["detail"]


@pytest.mark.parametrize(
    ("url", "parameter"),
    [
        ("/api/decision?day=oops", "day"),
        ("/api/decision", "day"),
        ("/api/decision?day=2026-01-02&cutoff=25:00", "cutoff"),
        ("/api/accuracy/summary?from=oops", "from"),
        ("/api/decision?day=2026-03-01", "day"),
        ("/api/accuracy/summary?from=2026-01-03&to=2026-01-02", "from"),
    ],
)
def test_every_invalid_input_response_is_one_string_naming_the_parameter(
    api_client: TestClient, url: str, parameter: str
) -> None:
    response = api_client.get(url)

    detail = response.json()["detail"]
    assert response.status_code == 422
    assert isinstance(detail, str)
    assert parameter in detail


def test_invalid_input_is_not_echoed_back_in_the_error(api_client: TestClient) -> None:
    detail = api_client.get("/api/decision?day=2026-01-02&cutoff=SECRET9").json()["detail"]

    assert "SECRET9" not in detail


def test_many_different_cutoffs_work_while_the_cache_stays_bounded(
    api_client: TestClient, wind_data: WindData
) -> None:
    # Regression: unlimited distinct cutoffs used to grow memory without limit.
    for minute in range(MAX_CACHED_CUTOFFS + 8):
        assert api_client.get(f"/api/accuracy/summary?cutoff=10:{minute:02d}").status_code == 200

    assert wind_data.cached_cutoff_count == MAX_CACHED_CUTOFFS


def test_post_method_is_not_allowed(api_client: TestClient) -> None:
    assert api_client.post("/api/meta").status_code == 405


def test_unknown_accuracy_path_returns_404(api_client: TestClient) -> None:
    assert api_client.get("/api/accuracy/nope").status_code == 404


def test_snapshot_unavailable_returns_503_without_leaking_the_path() -> None:
    def broken_loader() -> None:
        raise SnapshotError("Snapshot not found at C:/secret/dir/snapshot.json.gz")

    app.dependency_overrides[get_wind_data] = broken_loader
    try:
        response = TestClient(app).get("/api/meta")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "The data snapshot is unavailable."}
    assert "secret" not in response.text


def test_load_wind_data_reads_the_configured_snapshot_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    wind_snapshot: Snapshot,
    fresh_loader_cache: None,
) -> None:
    snapshot_path = tmp_path / "snapshot.json.gz"
    write_snapshot(wind_snapshot, snapshot_path)
    monkeypatch.setattr("app.routes.SNAPSHOT_PATH", snapshot_path)

    first = load_wind_data()

    assert first.snapshot == wind_snapshot
    assert load_wind_data() is first
    assert get_wind_data() is first


def test_load_wind_data_missing_file_raises_snapshot_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fresh_loader_cache: None
) -> None:
    monkeypatch.setattr("app.routes.SNAPSHOT_PATH", tmp_path / "missing.json.gz")

    with pytest.raises(SnapshotError):
        load_wind_data()


def test_committed_snapshot_decision_day_has_48_points_from_the_0730_forecast(
    client: TestClient,
) -> None:
    body: dict[str, Any] = client.get("/api/decision?day=2026-01-15").json()

    assert len(body["points"]) == 48
    assert body["forecast_publish_times_utc"] == ["2026-01-14T07:30:00Z"]
    assert body["cutoff_utc"] == "2026-01-14T09:00:00Z"
    assert body["missing_half_hours"] == 0


def test_committed_snapshot_summary_matches_the_phase_4_sanity_check(client: TestClient) -> None:
    summary = client.get("/api/accuracy/summary").json()["summary"]

    assert summary["sample_count"] == 1488
    assert summary["mae_mw"] == pytest.approx(2042.0, abs=0.05)
    assert summary["bias_mw"] == pytest.approx(-1747.9, abs=0.05)
