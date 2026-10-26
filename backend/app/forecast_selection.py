"""Pure logic: the forecast the buyer could see at decision time, and how it pairs with actuals.

No I/O lives here, so every rule can be tested with small hand-written examples.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import ACTUAL_HALF_HOUR_MINUTES, HALF_HOURS_PER_FORECAST_HOUR, UK_TIMEZONE_NAME
from app.schemas import ActualRow, ForecastRow

UK_TIMEZONE = ZoneInfo(UK_TIMEZONE_NAME)


@dataclass(frozen=True)
class ForecastActualPair:
    """One half-hour with the forecast that was used for it and what actually happened."""

    target_start_utc: datetime
    forecast_publish_time_utc: datetime
    horizon_hours: float
    forecast_generation_mw: float
    actual_generation_mw: float

    @property
    def error_mw(self) -> float:
        """Actual minus forecast.

        Negative: the forecast was too high (over-forecast), so the buyer bought too little wind
        cover and must fill a shortfall. Positive: the forecast was too low (surplus wind).
        """
        return self.actual_generation_mw - self.forecast_generation_mw


def uk_delivery_day(target_start_utc: datetime) -> date:
    """Return the UK calendar day that a target time belongs to."""
    return target_start_utc.astimezone(UK_TIMEZONE).date()


def compute_cutoff_utc(delivery_day: date, cutoff_time_uk: time) -> datetime:
    """Return the decision cutoff for a delivery day, in UTC.

    The buyer decides on the day before delivery, at cutoff_time_uk UK local time. Converting from
    UK local time keeps the cutoff correct when the clocks change.

    Raises:
        ValueError: If cutoff_time_uk carries a timezone (it must be plain UK local time).
    """
    if cutoff_time_uk.tzinfo is not None:
        raise ValueError("cutoff_time_uk must not have a timezone; it is UK local time")
    decision_day = delivery_day - timedelta(days=1)
    return datetime.combine(decision_day, cutoff_time_uk, tzinfo=UK_TIMEZONE).astimezone(UTC)


def select_decision_forecasts(
    forecasts: Iterable[ForecastRow], cutoff_time_uk: time
) -> list[ForecastRow]:
    """For each target hour, keep the latest forecast published at or before its cutoff.

    A forecast published after the cutoff is never used, because the buyer could not have seen it.
    A forecast published exactly at the cutoff is allowed. Target hours with no eligible forecast
    are left out. The result is sorted by target hour.
    """
    cutoff_by_day: dict[date, datetime] = {}
    latest_by_target: dict[datetime, ForecastRow] = {}
    for forecast in forecasts:
        delivery_day = uk_delivery_day(forecast.start_time_utc)
        if delivery_day not in cutoff_by_day:
            cutoff_by_day[delivery_day] = compute_cutoff_utc(delivery_day, cutoff_time_uk)
        if forecast.publish_time_utc > cutoff_by_day[delivery_day]:
            continue
        current = latest_by_target.get(forecast.start_time_utc)
        if current is None or forecast.publish_time_utc > current.publish_time_utc:
            latest_by_target[forecast.start_time_utc] = forecast
    return sorted(latest_by_target.values(), key=lambda forecast: forecast.start_time_utc)


def pair_forecasts_with_actuals(
    forecasts: Iterable[ForecastRow], actuals: Iterable[ActualRow]
) -> list[ForecastActualPair]:
    """Line each hourly forecast up with the actual half-hours it covers.

    An hourly forecast is applied to both half-hours of its hour (docs/DECISIONS.md D-004). The
    horizon is measured from publish time to the forecast's own target hour, so both half-hours
    share it. Half-hours without an actual value are skipped. Sorted by target, then publish time.
    """
    actual_mw_by_start = {actual.start_time_utc: actual.generation_mw for actual in actuals}
    pairs = []
    for forecast in forecasts:
        horizon_hours = (forecast.start_time_utc - forecast.publish_time_utc) / timedelta(hours=1)
        for half_hour_index in range(HALF_HOURS_PER_FORECAST_HOUR):
            offset = timedelta(minutes=ACTUAL_HALF_HOUR_MINUTES * half_hour_index)
            target_start_utc = forecast.start_time_utc + offset
            if target_start_utc not in actual_mw_by_start:
                continue
            pairs.append(
                ForecastActualPair(
                    target_start_utc=target_start_utc,
                    forecast_publish_time_utc=forecast.publish_time_utc,
                    horizon_hours=horizon_hours,
                    forecast_generation_mw=forecast.generation_mw,
                    actual_generation_mw=actual_mw_by_start[target_start_utc],
                )
            )
    return sorted(pairs, key=lambda pair: (pair.target_start_utc, pair.forecast_publish_time_utc))
