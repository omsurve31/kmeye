"""Tests for app/elexon_client.py. HTTP is mocked; the real Elexon API is never called."""

from collections.abc import Iterator
from datetime import UTC, date, datetime

import httpx
import pytest
import respx

from app.config import (
    ELEXON_ACTUALS_PATH,
    ELEXON_BASE_URL,
    ELEXON_MAX_ATTEMPTS,
    ELEXON_WIND_FORECAST_PATH,
)
from app.elexon_client import ElexonClient, RawRow, chunk_date_range, chunk_time_range
from app.errors import ElexonError

FORECAST_URL = f"{ELEXON_BASE_URL}{ELEXON_WIND_FORECAST_PATH}"
ACTUALS_URL = f"{ELEXON_BASE_URL}{ELEXON_ACTUALS_PATH}"
ROW: RawRow = {
    "dataset": "WINDFOR",
    "publishTime": "2026-01-01T07:30:00Z",
    "startTime": "2026-01-02T00:00:00Z",
    "generation": 15000,
}


@pytest.fixture
def elexon_client() -> Iterator[ElexonClient]:
    with httpx.Client() as http_client:
        yield ElexonClient(http_client)


def test_chunk_date_range_whole_delivery_window_returns_five_inclusive_weekly_chunks() -> None:
    chunks = chunk_date_range(date(2026, 1, 2), date(2026, 2, 1), chunk_days=7)

    assert chunks == [
        (date(2026, 1, 2), date(2026, 1, 8)),
        (date(2026, 1, 9), date(2026, 1, 15)),
        (date(2026, 1, 16), date(2026, 1, 22)),
        (date(2026, 1, 23), date(2026, 1, 29)),
        (date(2026, 1, 30), date(2026, 2, 1)),
    ]


def test_chunk_date_range_single_day_returns_one_chunk() -> None:
    assert chunk_date_range(date(2026, 1, 2), date(2026, 1, 2), chunk_days=7) == [
        (date(2026, 1, 2), date(2026, 1, 2))
    ]


def test_chunk_date_range_exact_multiple_has_no_empty_last_chunk() -> None:
    chunks = chunk_date_range(date(2026, 1, 1), date(2026, 1, 14), chunk_days=7)

    assert chunks == [
        (date(2026, 1, 1), date(2026, 1, 7)),
        (date(2026, 1, 8), date(2026, 1, 14)),
    ]


@pytest.mark.parametrize("chunk_days", [0, -1])
def test_chunk_date_range_non_positive_chunk_days_raises(chunk_days: int) -> None:
    with pytest.raises(ValueError, match="chunk_days"):
        chunk_date_range(date(2026, 1, 2), date(2026, 1, 3), chunk_days=chunk_days)


def test_chunk_date_range_first_day_after_last_day_raises() -> None:
    with pytest.raises(ValueError, match="first_day"):
        chunk_date_range(date(2026, 1, 3), date(2026, 1, 2), chunk_days=7)


def test_chunk_time_range_35_days_returns_five_contiguous_weekly_chunks() -> None:
    chunks = chunk_time_range(
        datetime(2025, 12, 29, tzinfo=UTC), datetime(2026, 2, 2, tzinfo=UTC), chunk_days=7
    )

    assert len(chunks) == 5
    assert chunks[0] == (datetime(2025, 12, 29, tzinfo=UTC), datetime(2026, 1, 5, tzinfo=UTC))
    assert chunks[-1] == (datetime(2026, 1, 26, tzinfo=UTC), datetime(2026, 2, 2, tzinfo=UTC))
    assert all(earlier[1] == later[0] for earlier, later in zip(chunks, chunks[1:], strict=False))


def test_chunk_time_range_partial_last_chunk_is_clipped_to_end() -> None:
    chunks = chunk_time_range(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 11, tzinfo=UTC), chunk_days=7
    )

    assert chunks == [
        (datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 8, tzinfo=UTC)),
        (datetime(2026, 1, 8, tzinfo=UTC), datetime(2026, 1, 11, tzinfo=UTC)),
    ]


def test_chunk_time_range_start_not_before_end_raises() -> None:
    moment = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="before"):
        chunk_time_range(moment, moment, chunk_days=7)


def test_chunk_time_range_non_positive_chunk_days_raises() -> None:
    with pytest.raises(ValueError, match="chunk_days"):
        chunk_time_range(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC), chunk_days=0
        )


def test_chunk_time_range_naive_datetime_raises() -> None:
    with pytest.raises(ValueError, match="timezone"):
        chunk_time_range(datetime(2026, 1, 1), datetime(2026, 1, 8, tzinfo=UTC), chunk_days=7)


def test_fetch_wind_forecast_rows_sends_publish_window_in_utc(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(200, json=[ROW]))

    rows = elexon_client.fetch_wind_forecast_rows(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 4, tzinfo=UTC)
    )

    assert rows == [ROW]
    assert dict(route.calls.last.request.url.params) == {
        "publishDateTimeFrom": "2026-01-01T00:00:00Z",
        "publishDateTimeTo": "2026-01-04T00:00:00Z",
    }


def test_fetch_wind_forecast_rows_long_window_makes_one_request_per_chunk(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    first_row = {**ROW, "generation": 1}
    second_row = {**ROW, "generation": 2}
    route = respx_mock.get(FORECAST_URL)
    route.side_effect = [
        httpx.Response(200, json=[first_row]),
        httpx.Response(200, json=[second_row]),
    ]

    rows = elexon_client.fetch_wind_forecast_rows(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 15, tzinfo=UTC)
    )

    assert rows == [first_row, second_row]
    assert route.call_count == 2


def test_fetch_wind_actual_rows_sends_settlement_dates_and_wind_filter(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(ACTUALS_URL).mock(return_value=httpx.Response(200, json=[]))

    rows = elexon_client.fetch_wind_actual_rows(date(2026, 1, 2), date(2026, 1, 2))

    assert rows == []
    assert dict(route.calls.last.request.url.params) == {
        "settlementDateFrom": "2026-01-02",
        "settlementDateTo": "2026-01-02",
        "fuelType": "WIND",
    }


@pytest.mark.parametrize("failure_status_code", [429, 500, 503])
def test_fetch_retries_retryable_status_and_then_succeeds(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient, failure_status_code: int
) -> None:
    route = respx_mock.get(FORECAST_URL)
    route.side_effect = [httpx.Response(failure_status_code), httpx.Response(200, json=[ROW])]

    rows = elexon_client.fetch_wind_forecast_rows(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
    )

    assert rows == [ROW]
    assert route.call_count == 2


def test_fetch_retries_timeout_and_then_succeeds(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(FORECAST_URL)
    route.side_effect = [httpx.ConnectTimeout("timed out"), httpx.Response(200, json=[ROW])]

    rows = elexon_client.fetch_wind_forecast_rows(
        datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
    )

    assert rows == [ROW]
    assert route.call_count == 2


def test_fetch_persistent_server_error_raises_after_max_attempts(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(503))

    with pytest.raises(ElexonError, match="503"):
        elexon_client.fetch_wind_forecast_rows(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )

    assert route.call_count == ELEXON_MAX_ATTEMPTS


def test_fetch_persistent_timeout_raises_after_max_attempts(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(FORECAST_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))

    with pytest.raises(ElexonError, match="timed out"):
        elexon_client.fetch_wind_forecast_rows(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )

    assert route.call_count == ELEXON_MAX_ATTEMPTS


def test_fetch_client_error_raises_without_retry(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    route = respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(400))

    with pytest.raises(ElexonError, match="400"):
        elexon_client.fetch_wind_forecast_rows(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )

    assert route.call_count == 1


def test_fetch_invalid_json_body_raises(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(200, text="<html>oops</html>"))

    with pytest.raises(ElexonError, match="not valid JSON"):
        elexon_client.fetch_wind_forecast_rows(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )


def test_fetch_json_object_instead_of_array_raises(
    respx_mock: respx.MockRouter, elexon_client: ElexonClient
) -> None:
    respx_mock.get(FORECAST_URL).mock(return_value=httpx.Response(200, json={"error": "x"}))

    with pytest.raises(ElexonError, match="JSON array"):
        elexon_client.fetch_wind_forecast_rows(
            datetime(2026, 1, 1, tzinfo=UTC), datetime(2026, 1, 2, tzinfo=UTC)
        )
