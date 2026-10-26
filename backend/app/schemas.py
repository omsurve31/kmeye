"""Pydantic models: API responses and the rows stored in the data snapshot."""

from datetime import date

from pydantic import AwareDatetime, BaseModel


class HealthResponse(BaseModel):
    """Response of the health check endpoint."""

    status: str


class ForecastRow(BaseModel):
    """An hourly wind forecast made at publish_time_utc for the hour starting at start_time_utc."""

    publish_time_utc: AwareDatetime
    start_time_utc: AwareDatetime
    generation_mw: float


class ActualRow(BaseModel):
    """Actual wind generation (average MW) for the half-hour starting at start_time_utc."""

    start_time_utc: AwareDatetime
    generation_mw: float


class DatasetSummary(BaseModel):
    """What ingestion did to one dataset: rows fetched, rows kept and why rows were dropped."""

    rows_fetched: int
    rows_kept: int
    rows_dropped: dict[str, int]


class Snapshot(BaseModel):
    """The committed data file: cleaned rows for the delivery window plus an ingestion audit."""

    first_delivery_day: date
    last_delivery_day: date
    forecast_summary: DatasetSummary
    actual_summary: DatasetSummary
    missing_actual_half_hours: int
    forecasts: list[ForecastRow]
    actuals: list[ActualRow]
