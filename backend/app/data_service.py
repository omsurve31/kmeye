"""Build API responses from the snapshot. Pure functions over an in-memory WindData."""

import threading
from datetime import date, datetime, time

from app.config import (
    ACTUAL_HALF_HOUR_MINUTES,
    CUTOFF_TEXT_FORMAT,
    DEFAULT_CUTOFF_TIME_UK,
    ERROR_DEFINITION,
    HALF_HOURS_PER_DAY,
    HISTOGRAM_BIN_WIDTH_MW,
    HORIZON_BIN_HOURS,
    MAX_CACHED_CUTOFFS,
    MINUTES_PER_HOUR,
    UK_TIMEZONE_NAME,
)
from app.errors import NoDataError
from app.forecast_selection import (
    UK_TIMEZONE,
    ForecastActualPair,
    compute_cutoff_utc,
    half_hour_starts,
    pair_forecasts_with_actuals,
    select_decision_forecasts,
    uk_delivery_day,
)
from app.metrics import (
    build_error_histogram,
    summarise_by_delivery_day,
    summarise_by_horizon,
    summarise_by_hour_of_day,
    summarise_errors,
)
from app.schemas import (
    AccuracySummaryResponse,
    DailyAccuracyResponse,
    DecisionPoint,
    DecisionResponse,
    DistributionResponse,
    ForecastRow,
    HorizonAccuracyResponse,
    HourlyAccuracyResponse,
    MetaResponse,
    SeriesPoint,
    SeriesResponse,
    Snapshot,
)


class WindData:
    """The snapshot plus cached results, so each cutoff is worked out only once."""

    def __init__(self, snapshot: Snapshot) -> None:
        self.snapshot = snapshot
        self._actual_mw_by_start = {a.start_time_utc: a.generation_mw for a in snapshot.actuals}
        self._decision_forecasts: dict[time, list[ForecastRow]] = {}
        self._decision_pairs: dict[time, list[ForecastActualPair]] = {}
        self._hour_bands: dict[time, dict[int, tuple[float, float]]] = {}
        self._all_pairs: list[ForecastActualPair] | None = None
        # Handlers run in a thread pool, so changes to the caches must not overlap.
        self._lock = threading.RLock()

    @property
    def cached_cutoff_count(self) -> int:
        """How many cutoffs currently have cached results."""
        return len(self._decision_forecasts)

    def actual_mw(self, start_time_utc: datetime) -> float | None:
        """Return the actual generation for a half-hour, or None if Elexon had no value."""
        return self._actual_mw_by_start.get(start_time_utc)

    def _evict_oldest_cutoff_if_full(self) -> None:
        """Keep memory bounded. Clients choose the cutoff and there are 1,440 possible values."""
        if len(self._decision_forecasts) < MAX_CACHED_CUTOFFS:
            return
        oldest_cutoff = next(iter(self._decision_forecasts))
        del self._decision_forecasts[oldest_cutoff]
        self._decision_pairs.pop(oldest_cutoff, None)
        self._hour_bands.pop(oldest_cutoff, None)

    def decision_forecasts(self, cutoff_time_uk: time) -> list[ForecastRow]:
        """The forecast the buyer could see for every target hour at this cutoff."""
        with self._lock:
            if cutoff_time_uk not in self._decision_forecasts:
                self._evict_oldest_cutoff_if_full()
                self._decision_forecasts[cutoff_time_uk] = select_decision_forecasts(
                    self.snapshot.forecasts, cutoff_time_uk
                )
            return self._decision_forecasts[cutoff_time_uk]

    def decision_pairs(self, cutoff_time_uk: time) -> list[ForecastActualPair]:
        """Decision-time forecasts paired with actuals, for every half-hour."""
        with self._lock:
            forecasts = self.decision_forecasts(cutoff_time_uk)
            if cutoff_time_uk not in self._decision_pairs:
                self._decision_pairs[cutoff_time_uk] = pair_forecasts_with_actuals(
                    forecasts, self.snapshot.actuals
                )
            return self._decision_pairs[cutoff_time_uk]

    def all_pairs(self) -> list[ForecastActualPair]:
        """Every published forecast paired with actuals (used for the lead-time view)."""
        with self._lock:
            if self._all_pairs is None:
                self._all_pairs = pair_forecasts_with_actuals(
                    self.snapshot.forecasts, self.snapshot.actuals
                )
            return self._all_pairs

    def hour_bands(self, cutoff_time_uk: time) -> dict[int, tuple[float, float]]:
        """P10 and P90 error in MW for each UK hour of the day, over the whole window.

        In-sample: the days being shown are part of the data the band is built from.
        """
        with self._lock:
            pairs = self.decision_pairs(cutoff_time_uk)
            if cutoff_time_uk not in self._hour_bands:
                self._hour_bands[cutoff_time_uk] = {
                    entry.hour_of_day: (entry.summary.error_p10_mw, entry.summary.error_p90_mw)
                    for entry in summarise_by_hour_of_day(pairs)
                }
            return self._hour_bands[cutoff_time_uk]


def format_cutoff(cutoff_time_uk: time) -> str:
    """Write a cutoff as HH:MM, the form the API uses."""
    return cutoff_time_uk.strftime(CUTOFF_TEXT_FORMAT)


def pairs_in_range(
    pairs: list[ForecastActualPair], first_day: date, last_day: date
) -> list[ForecastActualPair]:
    """Keep pairs whose UK delivery day is between first_day and last_day, both included."""
    return [p for p in pairs if first_day <= uk_delivery_day(p.target_start_utc) <= last_day]


def _pairs_or_raise(
    pairs: list[ForecastActualPair], first_day: date, last_day: date
) -> list[ForecastActualPair]:
    selected = pairs_in_range(pairs, first_day, last_day)
    if not selected:
        raise NoDataError("no forecast/actual data for the selected days")
    return selected


def build_meta(data: WindData) -> MetaResponse:
    """Describe the data window, the default assumptions and what ingestion kept."""
    snapshot = data.snapshot
    return MetaResponse(
        first_delivery_day=snapshot.first_delivery_day,
        last_delivery_day=snapshot.last_delivery_day,
        default_cutoff_time_uk=format_cutoff(DEFAULT_CUTOFF_TIME_UK),
        timezone=UK_TIMEZONE_NAME,
        error_definition=ERROR_DEFINITION,
        forecast_summary=snapshot.forecast_summary,
        actual_summary=snapshot.actual_summary,
        missing_actual_half_hours=snapshot.missing_actual_half_hours,
    )


def _build_decision_point(
    forecast: ForecastRow,
    start_time_utc: datetime,
    bands: dict[int, tuple[float, float]],
    data: WindData,
) -> DecisionPoint:
    band = bands.get(start_time_utc.astimezone(UK_TIMEZONE).hour)
    # Wind output cannot be negative, so the band stops at zero.
    return DecisionPoint(
        start_time_utc=start_time_utc,
        forecast_mw=forecast.generation_mw,
        forecast_publish_time_utc=forecast.publish_time_utc,
        band_low_mw=None if band is None else max(0.0, forecast.generation_mw + band[0]),
        band_high_mw=None if band is None else max(0.0, forecast.generation_mw + band[1]),
        actual_mw=data.actual_mw(start_time_utc),
    )


def build_decision(data: WindData, delivery_day: date, cutoff_time_uk: time) -> DecisionResponse:
    """The forecast available at the cutoff for one delivery day, with band and actuals.

    Raises:
        NoDataError: If no forecast had been published by the cutoff for that day.
    """
    forecasts = [
        f
        for f in data.decision_forecasts(cutoff_time_uk)
        if uk_delivery_day(f.start_time_utc) == delivery_day
    ]
    if not forecasts:
        raise NoDataError(
            f"no forecast was published before the {format_cutoff(cutoff_time_uk)} cutoff "
            f"for {delivery_day}"
        )
    bands = data.hour_bands(cutoff_time_uk)
    points = [
        _build_decision_point(forecast, start, bands, data)
        for forecast in forecasts
        for start in half_hour_starts(forecast.start_time_utc)
    ]
    forecast_values = [point.forecast_mw for point in points]
    hours_per_half_hour = ACTUAL_HALF_HOUR_MINUTES / MINUTES_PER_HOUR
    return DecisionResponse(
        delivery_day=delivery_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        cutoff_utc=compute_cutoff_utc(delivery_day, cutoff_time_uk),
        forecast_publish_times_utc=sorted({p.forecast_publish_time_utc for p in points}),
        expected_total_mwh=sum(forecast_values) * hours_per_half_hour,
        average_mw=sum(forecast_values) / len(forecast_values),
        peak_mw=max(forecast_values),
        minimum_mw=min(forecast_values),
        missing_half_hours=HALF_HOURS_PER_DAY - len(points),
        points=points,
    )


def build_series(
    data: WindData, first_day: date, last_day: date, cutoff_time_uk: time
) -> SeriesResponse:
    """Forecast against actual for every half-hour in the range."""
    pairs = _pairs_or_raise(data.decision_pairs(cutoff_time_uk), first_day, last_day)
    return SeriesResponse(
        first_day=first_day,
        last_day=last_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        points=[
            SeriesPoint(
                start_time_utc=p.target_start_utc,
                forecast_mw=p.forecast_generation_mw,
                actual_mw=p.actual_generation_mw,
                error_mw=p.error_mw,
            )
            for p in pairs
        ],
    )


def build_accuracy_summary(
    data: WindData, first_day: date, last_day: date, cutoff_time_uk: time
) -> AccuracySummaryResponse:
    """Headline accuracy of the decision-time forecast over the range."""
    pairs = _pairs_or_raise(data.decision_pairs(cutoff_time_uk), first_day, last_day)
    return AccuracySummaryResponse(
        first_day=first_day,
        last_day=last_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        summary=summarise_errors(pairs),
    )


def build_hourly_accuracy(
    data: WindData, first_day: date, last_day: date, cutoff_time_uk: time
) -> HourlyAccuracyResponse:
    """Decision-time accuracy for each UK hour of the day."""
    pairs = _pairs_or_raise(data.decision_pairs(cutoff_time_uk), first_day, last_day)
    return HourlyAccuracyResponse(
        first_day=first_day,
        last_day=last_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        hours=summarise_by_hour_of_day(pairs),
    )


def build_daily_accuracy(
    data: WindData, first_day: date, last_day: date, cutoff_time_uk: time
) -> DailyAccuracyResponse:
    """Decision-time accuracy for each delivery day."""
    pairs = _pairs_or_raise(data.decision_pairs(cutoff_time_uk), first_day, last_day)
    return DailyAccuracyResponse(
        first_day=first_day,
        last_day=last_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        days=summarise_by_delivery_day(pairs),
    )


def build_distribution(
    data: WindData, first_day: date, last_day: date, cutoff_time_uk: time
) -> DistributionResponse:
    """Histogram of decision-time errors, plus the summary that holds the percentiles."""
    pairs = _pairs_or_raise(data.decision_pairs(cutoff_time_uk), first_day, last_day)
    return DistributionResponse(
        first_day=first_day,
        last_day=last_day,
        cutoff_time_uk=format_cutoff(cutoff_time_uk),
        bin_width_mw=HISTOGRAM_BIN_WIDTH_MW,
        bins=build_error_histogram(pairs),
        summary=summarise_errors(pairs),
    )


def build_horizon_accuracy(
    data: WindData, first_day: date, last_day: date
) -> HorizonAccuracyResponse:
    """Accuracy by lead time, using every published forecast (not just the decision-time one)."""
    pairs = _pairs_or_raise(data.all_pairs(), first_day, last_day)
    return HorizonAccuracyResponse(
        first_day=first_day,
        last_day=last_day,
        bin_hours=HORIZON_BIN_HOURS,
        horizons=summarise_by_horizon(pairs),
    )
