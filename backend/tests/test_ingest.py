"""Tests for app/ingest.py: parsing, cleaning, snapshot building and the ingest entry point."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx

from app.config import (
    DELIVERY_WINDOW_START_UTC,
    ELEXON_ACTUALS_PATH,
    ELEXON_BASE_URL,
    ELEXON_WIND_FORECAST_PATH,
)
from app.elexon_client import RawRow
from app.errors import IngestError
from app.ingest import (
    build_snapshot,
    clean_actual_rows,
    clean_forecast_rows,
    count_missing_half_hours,
    main,
    run_ingest,
)
from app.schemas import ActualRow, DatasetSummary
from app.snapshot import read_snapshot

FORECAST_URL = f"{ELEXON_BASE_URL}{ELEXON_WIND_FORECAST_PATH}"
ACTUALS_URL = f"{ELEXON_BASE_URL}{ELEXON_ACTUALS_PATH}"
EXPECTED_HALF_HOURS_IN_WINDOW = 31 * 48


def _forecast_row(publish: str, start: str, generation: object = 1000) -> RawRow:
    return {
        "dataset": "WINDFOR",
        "publishTime": publish,
        "startTime": start,
        "generation": generation,
    }


def _actual_row(start: str, fuel_type: str = "WIND", generation: object = 1000) -> RawRow:
    return {
        "dataset": "FUELHH",
        "publishTime": start,
        "startTime": start,
        "fuelType": fuel_type,
        "generation": generation,
    }


def test_clean_forecast_rows_sample_keeps_valid_rows_and_counts_drops(
    windfor_rows: list[RawRow],
) -> None:
    rows, summary = clean_forecast_rows(windfor_rows)

    assert [(r.start_time_utc, r.publish_time_utc, r.generation_mw) for r in rows] == [
        (datetime(2026, 1, 2, 0, tzinfo=UTC), datetime(2026, 1, 1, 7, 30, tzinfo=UTC), 15000.0),
        (datetime(2026, 1, 2, 0, tzinfo=UTC), datetime(2026, 1, 1, 9, 30, tzinfo=UTC), 15100.0),
        (datetime(2026, 1, 2, 1, tzinfo=UTC), datetime(2026, 1, 1, 7, 30, tzinfo=UTC), 15200.0),
        (datetime(2026, 2, 1, 23, tzinfo=UTC), datetime(2026, 1, 31, 22, 30, tzinfo=UTC), 8000.0),
    ]
    assert summary == DatasetSummary(
        rows_fetched=9,
        rows_kept=4,
        rows_dropped={
            "duplicate": 1,
            "null_generation": 1,
            "outside_delivery_window": 2,
            "negative_horizon": 1,
        },
    )


def test_clean_forecast_rows_empty_input_returns_empty_result() -> None:
    rows, summary = clean_forecast_rows([])

    assert rows == []
    assert summary == DatasetSummary(rows_fetched=0, rows_kept=0, rows_dropped={})


@pytest.mark.parametrize(
    ("start_time", "should_be_kept"),
    [
        ("2026-01-01T23:00:00Z", False),
        ("2026-01-02T00:00:00Z", True),
        ("2026-02-01T23:00:00Z", True),
        ("2026-02-02T00:00:00Z", False),
    ],
)
def test_clean_forecast_rows_delivery_window_boundaries(
    start_time: str, should_be_kept: bool
) -> None:
    rows, _ = clean_forecast_rows([_forecast_row("2025-12-31T07:30:00Z", start_time)])

    assert (len(rows) == 1) is should_be_kept


def test_clean_forecast_rows_horizon_of_zero_is_kept() -> None:
    rows, _ = clean_forecast_rows([_forecast_row("2026-01-05T00:00:00Z", "2026-01-05T00:00:00Z")])

    assert len(rows) == 1


def test_clean_forecast_rows_published_after_target_start_is_dropped() -> None:
    rows, summary = clean_forecast_rows(
        [_forecast_row("2026-01-05T01:00:00Z", "2026-01-05T00:00:00Z")]
    )

    assert rows == []
    assert summary.rows_dropped == {"negative_horizon": 1}


def test_clean_forecast_rows_duplicate_key_keeps_first_value() -> None:
    first = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z", generation=1)
    second = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z", generation=2)

    rows, summary = clean_forecast_rows([first, second])

    assert [row.generation_mw for row in rows] == [1.0]
    assert summary.rows_dropped == {"duplicate": 1}


def test_clean_forecast_rows_output_is_sorted_by_target_then_publish_time() -> None:
    later_target = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T01:00:00Z")
    later_publish = _forecast_row("2026-01-01T09:30:00Z", "2026-01-02T00:00:00Z")
    earlier_publish = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z")

    rows, _ = clean_forecast_rows([later_target, later_publish, earlier_publish])

    assert [(r.start_time_utc.hour, r.publish_time_utc.hour) for r in rows] == [
        (0, 7),
        (0, 9),
        (1, 7),
    ]


def test_clean_forecast_rows_offset_timestamp_is_converted_to_utc() -> None:
    row = _forecast_row("2026-01-01T07:30:00+00:00", "2026-01-02T01:00:00+01:00")

    rows, _ = clean_forecast_rows([row])

    assert rows[0].start_time_utc == datetime(2026, 1, 2, 0, tzinfo=UTC)


def test_clean_forecast_rows_naive_timestamp_raises() -> None:
    row = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00")

    with pytest.raises(IngestError, match="timezone"):
        clean_forecast_rows([row])


def test_clean_forecast_rows_missing_key_reports_row_index() -> None:
    valid = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z")
    broken: RawRow = {"dataset": "WINDFOR", "publishTime": "2026-01-01T07:30:00Z", "generation": 1}

    with pytest.raises(IngestError, match="row 1"):
        clean_forecast_rows([valid, broken])


@pytest.mark.parametrize("bad_generation", ["abc", True, [1]])
def test_clean_forecast_rows_non_numeric_generation_raises(bad_generation: object) -> None:
    row = _forecast_row("2026-01-01T07:30:00Z", "2026-01-02T00:00:00Z", generation=bad_generation)

    with pytest.raises(IngestError, match="generation"):
        clean_forecast_rows([row])


def test_clean_forecast_rows_non_string_timestamp_raises() -> None:
    row: RawRow = {"publishTime": 12345, "startTime": "2026-01-02T00:00:00Z", "generation": 1}

    with pytest.raises(IngestError, match="timestamp must be a string"):
        clean_forecast_rows([row])


def test_clean_forecast_rows_unparseable_timestamp_raises() -> None:
    row = _forecast_row("not a time", "2026-01-02T00:00:00Z")

    with pytest.raises(IngestError, match="row 0"):
        clean_forecast_rows([row])


def test_clean_actual_rows_sample_keeps_wind_rows_and_counts_drops(
    fuelhh_rows: list[RawRow],
) -> None:
    rows, summary = clean_actual_rows(fuelhh_rows)

    assert [(r.start_time_utc, r.generation_mw) for r in rows] == [
        (datetime(2026, 1, 2, 0, 0, tzinfo=UTC), 14000.0),
        (datetime(2026, 1, 2, 0, 30, tzinfo=UTC), 14100.0),
        (datetime(2026, 2, 1, 23, 30, tzinfo=UTC), 5302.0),
    ]
    assert summary == DatasetSummary(
        rows_fetched=7,
        rows_kept=3,
        rows_dropped={
            "not_wind": 1,
            "duplicate": 1,
            "outside_delivery_window": 1,
            "null_generation": 1,
        },
    )


def test_clean_actual_rows_empty_input_returns_empty_result() -> None:
    rows, summary = clean_actual_rows([])

    assert rows == []
    assert summary == DatasetSummary(rows_fetched=0, rows_kept=0, rows_dropped={})


@pytest.mark.parametrize(
    ("start_time", "should_be_kept"),
    [
        ("2026-01-01T23:30:00Z", False),
        ("2026-01-02T00:00:00Z", True),
        ("2026-02-01T23:30:00Z", True),
        ("2026-02-02T00:00:00Z", False),
    ],
)
def test_clean_actual_rows_delivery_window_boundaries(
    start_time: str, should_be_kept: bool
) -> None:
    rows, _ = clean_actual_rows([_actual_row(start_time)])

    assert (len(rows) == 1) is should_be_kept


def test_clean_actual_rows_non_string_fuel_type_raises() -> None:
    broken: RawRow = {"fuelType": 7, "startTime": "2026-01-02T00:00:00Z", "generation": 1}

    with pytest.raises(IngestError, match="fuelType must be a string"):
        clean_actual_rows([broken])


def test_clean_actual_rows_missing_fuel_type_raises() -> None:
    broken: RawRow = {"startTime": "2026-01-02T00:00:00Z", "generation": 1}

    with pytest.raises(IngestError, match="row 0"):
        clean_actual_rows([broken])


def test_count_missing_half_hours_empty_actuals_reports_whole_window() -> None:
    assert count_missing_half_hours([]) == EXPECTED_HALF_HOURS_IN_WINDOW


def test_count_missing_half_hours_complete_window_reports_zero() -> None:
    actuals = [
        ActualRow(
            start_time_utc=DELIVERY_WINDOW_START_UTC + timedelta(minutes=30 * index),
            generation_mw=1.0,
        )
        for index in range(EXPECTED_HALF_HOURS_IN_WINDOW)
    ]

    assert count_missing_half_hours(actuals) == 0


def test_count_missing_half_hours_partial_window_reports_the_gap() -> None:
    actuals = [
        ActualRow(start_time_utc=DELIVERY_WINDOW_START_UTC, generation_mw=1.0),
        ActualRow(
            start_time_utc=DELIVERY_WINDOW_START_UTC + timedelta(minutes=30), generation_mw=1.0
        ),
    ]

    assert count_missing_half_hours(actuals) == EXPECTED_HALF_HOURS_IN_WINDOW - 2


def test_build_snapshot_sample_rows_fills_summaries_and_window(
    windfor_rows: list[RawRow], fuelhh_rows: list[RawRow]
) -> None:
    snapshot = build_snapshot(windfor_rows, fuelhh_rows)

    assert snapshot.first_delivery_day == date(2026, 1, 2)
    assert snapshot.last_delivery_day == date(2026, 2, 1)
    assert len(snapshot.forecasts) == 4
    assert len(snapshot.actuals) == 3
    assert snapshot.forecast_summary.rows_fetched == 9
    assert snapshot.actual_summary.rows_fetched == 7
    assert snapshot.missing_actual_half_hours == EXPECTED_HALF_HOURS_IN_WINDOW - 3


def test_run_ingest_fetches_cleans_and_writes_snapshot(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    windfor_rows: list[RawRow],
    fuelhh_rows: list[RawRow],
) -> None:
    forecast_route = respx_mock.get(FORECAST_URL).mock(
        return_value=httpx.Response(200, json=windfor_rows)
    )
    actuals_route = respx_mock.get(ACTUALS_URL).mock(
        return_value=httpx.Response(200, json=fuelhh_rows)
    )
    snapshot_path = tmp_path / "snapshot.json.gz"

    with httpx.Client() as http_client:
        snapshot = run_ingest(http_client, snapshot_path)

    assert forecast_route.call_count == 5
    assert actuals_route.call_count == 5
    assert len(snapshot.forecasts) == 4
    assert len(snapshot.actuals) == 3
    assert read_snapshot(snapshot_path) == snapshot


def test_main_success_returns_zero_and_writes_snapshot(
    respx_mock: respx.MockRouter,
    tmp_path: Path,
    windfor_rows: list[RawRow],
    fuelhh_rows: list[RawRow],
) -> None:
    respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=windfor_rows))
    respx_mock.get(ACTUALS_URL).mock(return_value=httpx.Response(200, json=fuelhh_rows))
    snapshot_path = tmp_path / "snapshot.json.gz"

    exit_code = main(snapshot_path)

    assert exit_code == 0
    assert snapshot_path.exists()


def test_main_elexon_failure_returns_one_and_writes_nothing(
    respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(500))
    snapshot_path = tmp_path / "snapshot.json.gz"

    exit_code = main(snapshot_path)

    assert exit_code == 1
    assert not snapshot_path.exists()


def test_main_malformed_rows_return_one_and_write_nothing(
    respx_mock: respx.MockRouter, tmp_path: Path
) -> None:
    respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=[{"oops": 1}]))
    respx_mock.get(ACTUALS_URL).mock(return_value=httpx.Response(200, json=[]))
    snapshot_path = tmp_path / "snapshot.json.gz"

    exit_code = main(snapshot_path)

    assert exit_code == 1
    assert not snapshot_path.exists()
