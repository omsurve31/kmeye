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
    # 90% of half-hours had an error no bigger than this, in either direction.
    abs_error_p90_mw: float
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


class MetaResponse(BaseModel):
    """What data the API serves and the assumptions behind it."""

    first_delivery_day: date
    last_delivery_day: date
    default_cutoff_time_uk: str
    timezone: str
    error_definition: str
    forecast_summary: DatasetSummary
    actual_summary: DatasetSummary
    missing_actual_half_hours: int


class DecisionPoint(BaseModel):
    """One half-hour of the decision view: the forecast the buyer saw and how it turned out."""

    start_time_utc: AwareDatetime
    forecast_mw: float
    forecast_publish_time_utc: AwareDatetime
    # Range the outturn usually fell in (forecast plus the P10 and P90 January error for this
    # hour of day); None when there is no error history for the hour.
    band_low_mw: float | None
    band_high_mw: float | None
    actual_mw: float | None


class DecisionResponse(BaseModel):
    """The forecast available at the cutoff for one delivery day."""

    delivery_day: date
    cutoff_time_uk: str
    cutoff_utc: AwareDatetime
    forecast_publish_times_utc: list[AwareDatetime]
    expected_total_mwh: float
    average_mw: float
    peak_mw: float
    minimum_mw: float
    missing_half_hours: int
    points: list[DecisionPoint]


class SeriesPoint(BaseModel):
    """One half-hour of forecast against actual."""

    start_time_utc: AwareDatetime
    forecast_mw: float
    actual_mw: float
    error_mw: float


class RangeResponse(BaseModel):
    """Delivery days covered by an accuracy response."""

    first_day: date
    last_day: date


class CutoffRangeResponse(RangeResponse):
    """An accuracy response that depends on the decision cutoff."""

    cutoff_time_uk: str


class SeriesResponse(CutoffRangeResponse):
    """Forecast against actual for every half-hour in the range."""

    points: list[SeriesPoint]


class AccuracySummaryResponse(CutoffRangeResponse):
    """Headline accuracy for the decision-time forecast."""

    summary: ErrorSummary


class HourlyAccuracyResponse(CutoffRangeResponse):
    """Accuracy for each UK hour of the day."""

    hours: list[HourOfDayErrors]


class DailyAccuracyResponse(CutoffRangeResponse):
    """Accuracy for each delivery day."""

    days: list[DayErrors]


class DistributionResponse(CutoffRangeResponse):
    """Histogram of errors plus the summary that holds the percentiles."""

    bin_width_mw: float
    bins: list[HistogramBin]
    summary: ErrorSummary


class HorizonAccuracyResponse(RangeResponse):
    """Accuracy by forecast lead time, using every published forecast."""

    bin_hours: float
    horizons: list[HorizonErrors]
