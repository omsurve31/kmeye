"""Settings and constants shared across the backend."""

from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

API_TITLE = "UK Wind Forecast Portal API"
API_PREFIX = "/api"

# Origin of the Vite dev server; the deployed frontend is served from the same host as the API.
CORS_ALLOWED_ORIGINS = ["http://localhost:5173"]

# Elexon Insights API (no API key). Paths and parameters are verified in docs/DATA_NOTES.md.
ELEXON_BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
ELEXON_WIND_FORECAST_PATH = "/datasets/WINDFOR/stream"
ELEXON_ACTUALS_PATH = "/datasets/FUELHH/stream"
WIND_FUEL_TYPE = "WIND"
ELEXON_TIMEOUT_SECONDS = 60.0
ELEXON_MAX_ATTEMPTS = 3
ELEXON_RETRY_BACKOFF_SECONDS = 1.0  # doubles after each failed attempt
ELEXON_RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
FETCH_CHUNK_DAYS = 7

# Scope (docs/DECISIONS.md D-001): decisions made in January 2026, so delivery days 2 Jan - 1 Feb.
FIRST_DELIVERY_DAY = date(2026, 1, 2)
LAST_DELIVERY_DAY = date(2026, 2, 1)
DELIVERY_WINDOW_START_UTC = datetime.combine(FIRST_DELIVERY_DAY, time.min, tzinfo=UTC)
# Exclusive end. UK time equals UTC in winter, so UTC days are the same as UK days here.
DELIVERY_WINDOW_END_UTC = datetime.combine(
    LAST_DELIVERY_DAY + timedelta(days=1), time.min, tzinfo=UTC
)
ACTUAL_HALF_HOUR_MINUTES = 30

# The longest forecast horizon is 66.5 hours (docs/DATA_NOTES.md), so forecasts published from
# 29 Dec cover the first delivery day. Nothing published after the window can be non-negative.
FORECAST_PUBLISH_FROM_UTC = datetime(2025, 12, 29, tzinfo=UTC)
FORECAST_PUBLISH_TO_UTC = DELIVERY_WINDOW_END_UTC

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT_PATH = DATA_DIR / "snapshot.json.gz"
