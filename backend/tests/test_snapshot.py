"""Tests for app/snapshot.py: reading and writing the committed data snapshot."""

import gzip
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.errors import SnapshotError
from app.schemas import ActualRow, DatasetSummary, ForecastRow, Snapshot
from app.snapshot import read_snapshot, write_snapshot


def _snapshot() -> Snapshot:
    return Snapshot(
        first_delivery_day=date(2026, 1, 2),
        last_delivery_day=date(2026, 2, 1),
        forecast_summary=DatasetSummary(rows_fetched=2, rows_kept=1, rows_dropped={"duplicate": 1}),
        actual_summary=DatasetSummary(rows_fetched=1, rows_kept=1, rows_dropped={}),
        missing_actual_half_hours=1487,
        forecasts=[
            ForecastRow(
                publish_time_utc=datetime(2026, 1, 1, 7, 30, tzinfo=UTC),
                start_time_utc=datetime(2026, 1, 2, tzinfo=UTC),
                generation_mw=15000.0,
            )
        ],
        actuals=[ActualRow(start_time_utc=datetime(2026, 1, 2, tzinfo=UTC), generation_mw=14000.0)],
    )


def test_write_then_read_snapshot_roundtrips_exactly(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json.gz"

    write_snapshot(_snapshot(), path)

    assert read_snapshot(path) == _snapshot()


def test_write_snapshot_creates_missing_parent_directory(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "data" / "snapshot.json.gz"

    write_snapshot(_snapshot(), path)

    assert path.exists()


def test_write_snapshot_same_input_gives_identical_bytes(tmp_path: Path) -> None:
    first_path = tmp_path / "first" / "snapshot.json.gz"
    second_path = tmp_path / "second" / "renamed.json.gz"

    write_snapshot(_snapshot(), first_path)
    write_snapshot(_snapshot(), second_path)

    assert first_path.read_bytes() == second_path.read_bytes()


def test_read_snapshot_missing_file_tells_user_to_run_ingest(tmp_path: Path) -> None:
    with pytest.raises(SnapshotError, match="python -m app.ingest"):
        read_snapshot(tmp_path / "missing.json.gz")


def test_read_snapshot_file_that_is_not_gzip_raises(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json.gz"
    path.write_bytes(b"this is not gzip")

    with pytest.raises(SnapshotError, match="corrupt"):
        read_snapshot(path)


def test_read_snapshot_gzip_with_wrong_content_raises(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json.gz"
    path.write_bytes(gzip.compress(b'{"unexpected": 1}'))

    with pytest.raises(SnapshotError, match="corrupt"):
        read_snapshot(path)
