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

# Decision rule (docs/DECISIONS.md D-007). Assumption: the buyer decides at this UK local time on
# the day before delivery. Real day-ahead gate closures differ by venue.
UK_TIMEZONE_NAME = "Europe/London"
DEFAULT_CUTOFF_TIME_UK = time(9, 0)
# WINDFOR is hourly and FUELHH is half-hourly, so one forecast covers two actual half-hours (D-004).
HALF_HOURS_PER_FORECAST_HOUR = 2

# API. The cutoff is sent as HH:MM UK time, for example 09:00.
DEFAULT_CUTOFF_TEXT = "09:00"
CUTOFF_TEXT_FORMAT = "%H:%M"
CUTOFF_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"
HALF_HOURS_PER_DAY = 48
# Results are cached per cutoff. Cutoffs come from clients (1,440 possible values), so the cache is
# bounded to stop a client from using up memory by trying them all.
MAX_CACHED_CUTOFFS = 32
MINUTES_PER_HOUR = 60
ERROR_DEFINITION = (
    "Error = actual - forecast, in MW. A negative error means the forecast was too high "
    "(over-forecast), so the buyer is short. A positive error means the forecast was too low "
    "(surplus wind)."
)

# Accuracy metrics.
PERCENT_SCALE = 100.0
HISTOGRAM_BIN_WIDTH_MW = 500.0
HORIZON_BIN_HOURS = 6.0
PERCENTILE_5 = 5.0
PERCENTILE_10 = 10.0
PERCENTILE_50 = 50.0
PERCENTILE_90 = 90.0
PERCENTILE_95 = 95.0
