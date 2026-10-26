"""Fetch Elexon wind data, clean it and save the snapshot. Run with: python -m app.ingest."""

import logging
import sys
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.config import (
    ACTUAL_HALF_HOUR_MINUTES,
    DELIVERY_WINDOW_END_UTC,
    DELIVERY_WINDOW_START_UTC,
    FIRST_DELIVERY_DAY,
    FORECAST_PUBLISH_FROM_UTC,
    FORECAST_PUBLISH_TO_UTC,
    LAST_DELIVERY_DAY,
    SNAPSHOT_PATH,
    WIND_FUEL_TYPE,
)
from app.elexon_client import ElexonClient, RawRow
from app.errors import ElexonError, IngestError
from app.schemas import ActualRow, DatasetSummary, ForecastRow, Snapshot
from app.snapshot import write_snapshot

logger = logging.getLogger(__name__)


def _parse_time_utc(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(UTC)


def _parse_generation_mw(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("generation must be a number")
    return float(value)


def _is_in_delivery_window(moment: datetime) -> bool:
    return DELIVERY_WINDOW_START_UTC <= moment < DELIVERY_WINDOW_END_UTC


def _parse_forecast_row(raw: RawRow, index: int) -> ForecastRow | None:
    """Return the typed row, or None when Elexon reports no generation value."""
    try:
        generation_mw = _parse_generation_mw(raw["generation"])
        publish_time_utc = _parse_time_utc(raw["publishTime"])
        start_time_utc = _parse_time_utc(raw["startTime"])
    except (KeyError, TypeError, ValueError) as error:
        raise IngestError(f"WINDFOR row {index} is malformed: {error!r}") from error
    if generation_mw is None:
        return None
    return ForecastRow(
        publish_time_utc=publish_time_utc,
        start_time_utc=start_time_utc,
        generation_mw=generation_mw,
    )


def _parse_actual_fields(raw: RawRow, index: int) -> tuple[str, datetime, float | None]:
    try:
        fuel_type = raw["fuelType"]
        if not isinstance(fuel_type, str):
            raise ValueError("fuelType must be a string")
        return fuel_type, _parse_time_utc(raw["startTime"]), _parse_generation_mw(raw["generation"])
    except (KeyError, TypeError, ValueError) as error:
        raise IngestError(f"FUELHH row {index} is malformed: {error!r}") from error


def clean_forecast_rows(raw_rows: list[RawRow]) -> tuple[list[ForecastRow], DatasetSummary]:
    """Parse WINDFOR rows and keep only those usable for a day-ahead decision.

    A row is dropped when it has no value, targets an hour outside the delivery window, was
    published after its target hour started (negative horizon, useless for day-ahead buying), or
    repeats a (publish time, target hour) pair already seen; the first copy wins.
    """
    dropped: Counter[str] = Counter()
    kept_by_key: dict[tuple[datetime, datetime], ForecastRow] = {}
    for index, raw in enumerate(raw_rows):
        row = _parse_forecast_row(raw, index)
        if row is None:
            dropped["null_generation"] += 1
        elif not _is_in_delivery_window(row.start_time_utc):
            dropped["outside_delivery_window"] += 1
        elif row.start_time_utc < row.publish_time_utc:
            dropped["negative_horizon"] += 1
        elif (row.publish_time_utc, row.start_time_utc) in kept_by_key:
            dropped["duplicate"] += 1
        else:
            kept_by_key[(row.publish_time_utc, row.start_time_utc)] = row
    kept = sorted(kept_by_key.values(), key=lambda r: (r.start_time_utc, r.publish_time_utc))
    summary = DatasetSummary(
        rows_fetched=len(raw_rows), rows_kept=len(kept), rows_dropped=dict(dropped)
    )
    return kept, summary


def clean_actual_rows(raw_rows: list[RawRow]) -> tuple[list[ActualRow], DatasetSummary]:
    """Parse FUELHH rows and keep one WIND value per half-hour inside the delivery window.

    The API is asked for WIND only, but the fuel type is checked again here as a safeguard.
    """
    dropped: Counter[str] = Counter()
    kept_by_start: dict[datetime, ActualRow] = {}
    for index, raw in enumerate(raw_rows):
        fuel_type, start_time_utc, generation_mw = _parse_actual_fields(raw, index)
        if fuel_type != WIND_FUEL_TYPE:
            dropped["not_wind"] += 1
        elif generation_mw is None:
            dropped["null_generation"] += 1
        elif not _is_in_delivery_window(start_time_utc):
            dropped["outside_delivery_window"] += 1
        elif start_time_utc in kept_by_start:
            dropped["duplicate"] += 1
        else:
            kept_by_start[start_time_utc] = ActualRow(
                start_time_utc=start_time_utc, generation_mw=generation_mw
            )
    kept = sorted(kept_by_start.values(), key=lambda r: r.start_time_utc)
    summary = DatasetSummary(
        rows_fetched=len(raw_rows), rows_kept=len(kept), rows_dropped=dict(dropped)
    )
    return kept, summary


def count_missing_half_hours(actuals: list[ActualRow]) -> int:
    """Count half-hours in the delivery window that have no actual value."""
    window = DELIVERY_WINDOW_END_UTC - DELIVERY_WINDOW_START_UTC
    expected_half_hours = window // timedelta(minutes=ACTUAL_HALF_HOUR_MINUTES)
    return expected_half_hours - len({row.start_time_utc for row in actuals})


def build_snapshot(raw_forecasts: list[RawRow], raw_actuals: list[RawRow]) -> Snapshot:
    """Clean both raw datasets and combine them into a snapshot."""
    forecasts, forecast_summary = clean_forecast_rows(raw_forecasts)
    actuals, actual_summary = clean_actual_rows(raw_actuals)
    return Snapshot(
        first_delivery_day=FIRST_DELIVERY_DAY,
        last_delivery_day=LAST_DELIVERY_DAY,
        forecast_summary=forecast_summary,
        actual_summary=actual_summary,
        missing_actual_half_hours=count_missing_half_hours(actuals),
        forecasts=forecasts,
        actuals=actuals,
    )


def run_ingest(http_client: httpx.Client, snapshot_path: Path) -> Snapshot:
    """Fetch, clean and save the snapshot. Nothing is written if fetching or cleaning fails."""
    client = ElexonClient(http_client)
    raw_forecasts = client.fetch_wind_forecast_rows(
        FORECAST_PUBLISH_FROM_UTC, FORECAST_PUBLISH_TO_UTC
    )
    raw_actuals = client.fetch_wind_actual_rows(FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY)
    snapshot = build_snapshot(raw_forecasts, raw_actuals)
    write_snapshot(snapshot, snapshot_path)
    logger.info("Forecasts: %s", snapshot.forecast_summary.model_dump())
    logger.info("Actuals: %s", snapshot.actual_summary.model_dump())
    logger.info("Missing actual half-hours: %d", snapshot.missing_actual_half_hours)
    logger.info("Snapshot written to %s", snapshot_path)
    return snapshot


def main(snapshot_path: Path = SNAPSHOT_PATH) -> int:
    """Command-line entry point. Returns the process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        with httpx.Client() as http_client:
            run_ingest(http_client, snapshot_path)
    except (ElexonError, IngestError) as error:
        logger.error("Ingest failed: %s", error)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
