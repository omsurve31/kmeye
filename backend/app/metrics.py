"""Pure accuracy maths for wind forecasts. Error is always actual minus forecast, in MW.

No I/O and no pandas: plain Python keeps every formula visible and easy to check by hand.
"""

import math
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import date

from app.config import (
    HISTOGRAM_BIN_WIDTH_MW,
    HORIZON_BIN_HOURS,
    PERCENT_SCALE,
    PERCENTILE_5,
    PERCENTILE_10,
    PERCENTILE_50,
    PERCENTILE_90,
    PERCENTILE_95,
)
from app.errors import NoDataError
from app.forecast_selection import UK_TIMEZONE, ForecastActualPair, uk_delivery_day
from app.schemas import (
    DayErrors,
    ErrorSummary,
    HistogramBin,
    HorizonErrors,
    HourOfDayErrors,
)


def percentile(sorted_values: Sequence[float], level: float) -> float:
    """Return a percentile of already-sorted values, interpolating between neighbouring values.

    Example: for [10, 20, 30, 40] the 25th percentile sits at position 0.75, which is
    10 + 0.75 * (20 - 10) = 17.5.

    Raises:
        ValueError: If the values are empty or the level is not between 0 and 100.
    """
    if not sorted_values:
        raise ValueError("cannot take a percentile of an empty list")
    if not 0 <= level <= PERCENT_SCALE:
        raise ValueError("percentile level must be between 0 and 100")
    position = (len(sorted_values) - 1) * level / PERCENT_SCALE
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    gap = sorted_values[upper_index] - sorted_values[lower_index]
    return sorted_values[lower_index] + gap * (position - lower_index)


def summarise_errors(pairs: Sequence[ForecastActualPair]) -> ErrorSummary:
    """Summarise forecast accuracy over a set of half-hours.

    Raises:
        NoDataError: If there are no pairs.
    """
    if not pairs:
        raise NoDataError("no forecast/actual pairs to summarise")
    errors = sorted(pair.error_mw for pair in pairs)
    count = len(errors)
    absolute_errors = sorted(abs(error) for error in errors)
    mae_mw = sum(absolute_errors) / count
    mean_actual_mw = sum(pair.actual_generation_mw for pair in pairs) / count
    # MAE as a share of mean output. Plain MAPE is avoided: wind output can be near zero, which
    # would make a per-half-hour percentage explode.
    normalised_mae_percent = (
        mae_mw / mean_actual_mw * PERCENT_SCALE if mean_actual_mw != 0 else None
    )
    return ErrorSummary(
        sample_count=count,
        mae_mw=mae_mw,
        rmse_mw=math.sqrt(sum(error * error for error in errors) / count),
        bias_mw=sum(errors) / count,
        mean_actual_mw=mean_actual_mw,
        normalised_mae_percent=normalised_mae_percent,
        error_p5_mw=percentile(errors, PERCENTILE_5),
        error_p10_mw=percentile(errors, PERCENTILE_10),
        error_p50_mw=percentile(errors, PERCENTILE_50),
        error_p90_mw=percentile(errors, PERCENTILE_90),
        error_p95_mw=percentile(errors, PERCENTILE_95),
        abs_error_p90_mw=percentile(absolute_errors, PERCENTILE_90),
        over_forecast_fraction=sum(error < 0 for error in errors) / count,
    )


def build_error_histogram(
    pairs: Sequence[ForecastActualPair], bin_width_mw: float = HISTOGRAM_BIN_WIDTH_MW
) -> list[HistogramBin]:
    """Count errors in equal-width bins. Empty bins between the extremes are included.

    A bin includes its start and excludes its end, so an error on an edge goes in the upper bin.

    Raises:
        ValueError: If bin_width_mw is not positive.
    """
    if bin_width_mw <= 0:
        raise ValueError("bin_width_mw must be positive")
    counts = Counter(math.floor(pair.error_mw / bin_width_mw) for pair in pairs)
    if not counts:
        return []
    return [
        HistogramBin(
            bin_start_mw=index * bin_width_mw,
            bin_end_mw=(index + 1) * bin_width_mw,
            count=counts[index],
        )
        for index in range(min(counts), max(counts) + 1)
    ]


def _group_pairs[GroupKey: (int, float, date)](
    pairs: Sequence[ForecastActualPair], key_of: Callable[[ForecastActualPair], GroupKey]
) -> dict[GroupKey, list[ForecastActualPair]]:
    groups: dict[GroupKey, list[ForecastActualPair]] = defaultdict(list)
    for pair in pairs:
        groups[key_of(pair)].append(pair)
    return groups


def summarise_by_hour_of_day(pairs: Sequence[ForecastActualPair]) -> list[HourOfDayErrors]:
    """Accuracy for each UK hour of the day (0 to 23), in hour order."""
    groups = _group_pairs(pairs, lambda pair: pair.target_start_utc.astimezone(UK_TIMEZONE).hour)
    return [
        HourOfDayErrors(hour_of_day=hour, summary=summarise_errors(group))
        for hour, group in sorted(groups.items())
    ]


def summarise_by_delivery_day(pairs: Sequence[ForecastActualPair]) -> list[DayErrors]:
    """Accuracy for each UK delivery day, in date order."""
    groups = _group_pairs(pairs, lambda pair: uk_delivery_day(pair.target_start_utc))
    return [
        DayErrors(delivery_day=day, summary=summarise_errors(group))
        for day, group in sorted(groups.items())
    ]


def summarise_by_horizon(
    pairs: Sequence[ForecastActualPair], bin_hours: float = HORIZON_BIN_HOURS
) -> list[HorizonErrors]:
    """Accuracy by how long before the target the forecast was published, in bins of bin_hours.

    A bin includes its start and excludes its end.

    Raises:
        ValueError: If bin_hours is not positive.
    """
    if bin_hours <= 0:
        raise ValueError("bin_hours must be positive")
    groups = _group_pairs(
        pairs, lambda pair: math.floor(pair.horizon_hours / bin_hours) * bin_hours
    )
    return [
        HorizonErrors(
            horizon_start_hours=start_hours,
            horizon_end_hours=start_hours + bin_hours,
            summary=summarise_errors(group),
        )
        for start_hours, group in sorted(groups.items())
    ]
