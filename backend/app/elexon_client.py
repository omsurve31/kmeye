"""HTTP access to the Elexon Insights API: chunking, retries and clear errors."""

import logging
import time
from datetime import UTC, date, datetime, timedelta

import httpx

from app.config import (
    ELEXON_ACTUALS_PATH,
    ELEXON_BASE_URL,
    ELEXON_MAX_ATTEMPTS,
    ELEXON_RETRY_BACKOFF_SECONDS,
    ELEXON_RETRYABLE_STATUS_CODES,
    ELEXON_TIMEOUT_SECONDS,
    ELEXON_WIND_FORECAST_PATH,
    FETCH_CHUNK_DAYS,
    WIND_FUEL_TYPE,
)
from app.errors import ElexonError

logger = logging.getLogger(__name__)

# One raw JSON object as returned by Elexon; ingest.py checks and converts it into typed rows.
RawRow = dict[str, object]


def chunk_date_range(first_day: date, last_day: date, chunk_days: int) -> list[tuple[date, date]]:
    """Split first_day..last_day (both inclusive) into consecutive inclusive chunks."""
    if chunk_days < 1:
        raise ValueError("chunk_days must be at least 1")
    if first_day > last_day:
        raise ValueError("first_day must not be after last_day")
    chunks = []
    chunk_first = first_day
    while chunk_first <= last_day:
        chunk_last = min(chunk_first + timedelta(days=chunk_days - 1), last_day)
        chunks.append((chunk_first, chunk_last))
        chunk_first = chunk_last + timedelta(days=1)
    return chunks


def chunk_time_range(
    start: datetime, end: datetime, chunk_days: int
) -> list[tuple[datetime, datetime]]:
    """Split start..end into consecutive chunks that share boundaries; the last is clipped."""
    if chunk_days < 1:
        raise ValueError("chunk_days must be at least 1")
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("start and end must have a timezone")
    if start >= end:
        raise ValueError("start must be before end")
    chunks = []
    chunk_start = start
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(days=chunk_days), end)
        chunks.append((chunk_start, chunk_end))
        chunk_start = chunk_end
    return chunks


def _format_utc(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _decode_rows(response: httpx.Response) -> list[RawRow]:
    try:
        payload = response.json()
    except ValueError as error:
        raise ElexonError("Elexon response was not valid JSON") from error
    if not isinstance(payload, list):
        raise ElexonError("Elexon response was not a JSON array")
    return payload


class ElexonClient:
    """Fetches raw wind rows from Elexon, one request per chunk, with retries."""

    def __init__(self, http_client: httpx.Client) -> None:
        self._http_client = http_client

    def fetch_wind_forecast_rows(
        self, publish_from_utc: datetime, publish_to_utc: datetime
    ) -> list[RawRow]:
        """Fetch every WINDFOR forecast published between the two times."""
        rows: list[RawRow] = []
        for chunk_start, chunk_end in chunk_time_range(
            publish_from_utc, publish_to_utc, FETCH_CHUNK_DAYS
        ):
            params = {
                "publishDateTimeFrom": _format_utc(chunk_start),
                "publishDateTimeTo": _format_utc(chunk_end),
            }
            rows.extend(self._get_rows(ELEXON_WIND_FORECAST_PATH, params))
        return rows

    def fetch_wind_actual_rows(self, first_day: date, last_day: date) -> list[RawRow]:
        """Fetch FUELHH wind generation for the settlement dates first_day..last_day."""
        rows: list[RawRow] = []
        for chunk_first, chunk_last in chunk_date_range(first_day, last_day, FETCH_CHUNK_DAYS):
            params = {
                "settlementDateFrom": chunk_first.isoformat(),
                "settlementDateTo": chunk_last.isoformat(),
                "fuelType": WIND_FUEL_TYPE,
            }
            rows.extend(self._get_rows(ELEXON_ACTUALS_PATH, params))
        return rows

    def _get_rows(self, path: str, params: dict[str, str]) -> list[RawRow]:
        """GET one endpoint, retrying timeouts, network errors and 429/5xx responses."""
        url = f"{ELEXON_BASE_URL}{path}"
        last_problem = ""
        for attempt_number in range(1, ELEXON_MAX_ATTEMPTS + 1):
            try:
                response = self._http_client.get(url, params=params, timeout=ELEXON_TIMEOUT_SECONDS)
            except httpx.TransportError as error:
                last_problem = f"{type(error).__name__}: {error}"
            else:
                if response.is_success:
                    return _decode_rows(response)
                if response.status_code not in ELEXON_RETRYABLE_STATUS_CODES:
                    raise ElexonError(f"Elexon returned HTTP {response.status_code} for {path}")
                last_problem = f"HTTP {response.status_code}"
            logger.warning(
                "Elexon request to %s failed (attempt %d of %d): %s",
                path,
                attempt_number,
                ELEXON_MAX_ATTEMPTS,
                last_problem,
            )
            if attempt_number < ELEXON_MAX_ATTEMPTS:
                time.sleep(ELEXON_RETRY_BACKOFF_SECONDS * 2 ** (attempt_number - 1))
        raise ElexonError(
            f"Elexon request to {path} failed after {ELEXON_MAX_ATTEMPTS} attempts: {last_problem}"
        )
