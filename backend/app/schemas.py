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


class ErrorSummary(BaseModel):
    """Accuracy of a set of forecasts.

    Error is actual minus forecast, in MW: negative means the forecast was too high (the buyer is
    short), positive means it was too low (surplus wind).
    """

    sample_count: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    mean_actual_mw: float
    # MAE as a percentage of mean actual generation; None when the mean actual is zero.
    normalised_mae_percent: float | None
    error_p5_mw: float
    error_p10_mw: float
    error_p50_mw: float
    error_p90_mw: float
    error_p95_mw: float
    # Share of half-hours (0 to 1) where the forecast was too high.
    over_forecast_fraction: float


class HistogramBin(BaseModel):
    """One bar of the error histogram: errors from bin_start_mw (included) to bin_end_mw."""

    bin_start_mw: float
    bin_end_mw: float
    count: int


class HourOfDayErrors(BaseModel):
    """Accuracy for one UK hour of the day."""

    hour_of_day: int
    summary: ErrorSummary


class DayErrors(BaseModel):
    """Accuracy for one delivery day."""

    delivery_day: date
    summary: ErrorSummary


class HorizonErrors(BaseModel):
    """Accuracy for forecasts published between horizon_start_hours and horizon_end_hours ahead."""

    horizon_start_hours: float
    horizon_end_hours: float
    summary: ErrorSummary
