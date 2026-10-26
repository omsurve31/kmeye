"""HTTP endpoints. Each handler only checks its input and calls a builder in data_service."""

from dataclasses import dataclass
from datetime import date, datetime, time
from functools import cache
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import (
    API_PREFIX,
    CUTOFF_PATTERN,
    CUTOFF_TEXT_FORMAT,
    DEFAULT_CUTOFF_TEXT,
    FIRST_DELIVERY_DAY,
    LAST_DELIVERY_DAY,
    SNAPSHOT_PATH,
)
from app.data_service import (
    WindData,
    build_accuracy_summary,
    build_daily_accuracy,
    build_decision,
    build_distribution,
    build_horizon_accuracy,
    build_hourly_accuracy,
    build_meta,
    build_series,
)
from app.schemas import (
    AccuracySummaryResponse,
    DailyAccuracyResponse,
    DecisionResponse,
    DistributionResponse,
    HorizonAccuracyResponse,
    HourlyAccuracyResponse,
    MetaResponse,
    SeriesResponse,
)
from app.snapshot import read_snapshot

router = APIRouter(prefix=API_PREFIX)
DELIVERY_WINDOW_TEXT = f"{FIRST_DELIVERY_DAY.isoformat()} and {LAST_DELIVERY_DAY.isoformat()}"


@cache
def load_wind_data() -> WindData:
    """Read the committed snapshot once and keep it in memory (failures are not cached)."""
    return WindData(read_snapshot(SNAPSHOT_PATH))


def get_wind_data() -> WindData:
    """Dependency that gives handlers the data; tests replace it with a small snapshot."""
    return load_wind_data()


@dataclass(frozen=True)
class DayRange:
    """A validated range of delivery days, both ends included."""

    first_day: date
    last_day: date


def _check_in_window(value: date, name: str) -> None:
    if not FIRST_DELIVERY_DAY <= value <= LAST_DELIVERY_DAY:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must be a delivery day between {DELIVERY_WINDOW_TEXT}",
        )


def delivery_day_param(
    day: Annotated[date, Query(description="Delivery day, YYYY-MM-DD, 2 Jan to 1 Feb 2026")],
) -> date:
    """Validate the delivery day of the decision view."""
    _check_in_window(day, "day")
    return day


def day_range_param(
    from_day: Annotated[date | None, Query(alias="from", description="First delivery day")] = None,
    to_day: Annotated[date | None, Query(alias="to", description="Last delivery day")] = None,
) -> DayRange:
    """Validate an optional range of delivery days; it defaults to the whole window."""
    for value, name in ((from_day, "from"), (to_day, "to")):
        if value is not None:
            _check_in_window(value, name)
    first_day = from_day or FIRST_DELIVERY_DAY
    last_day = to_day or LAST_DELIVERY_DAY
    if first_day > last_day:
        raise HTTPException(status_code=422, detail="from must not be after to")
    return DayRange(first_day=first_day, last_day=last_day)


def parse_cutoff(
    cutoff: Annotated[
        str,
        Query(
            pattern=CUTOFF_PATTERN,
            max_length=5,
            description="Decision cutoff on the day before delivery, HH:MM UK time",
        ),
    ] = DEFAULT_CUTOFF_TEXT,
) -> time:
    """Turn the validated HH:MM text into a time of day."""
    return datetime.strptime(cutoff, CUTOFF_TEXT_FORMAT).time()


WindDataDep = Annotated[WindData, Depends(get_wind_data)]
CutoffDep = Annotated[time, Depends(parse_cutoff)]
DayRangeDep = Annotated[DayRange, Depends(day_range_param)]
DeliveryDayDep = Annotated[date, Depends(delivery_day_param)]


@router.get("/meta", response_model=MetaResponse)
def read_meta(data: WindDataDep) -> MetaResponse:
    """Delivery window, default assumptions and what ingestion kept."""
    return build_meta(data)


@router.get("/decision", response_model=DecisionResponse)
def read_decision(day: DeliveryDayDep, cutoff: CutoffDep, data: WindDataDep) -> DecisionResponse:
    """The forecast available at the cutoff for one delivery day."""
    return build_decision(data, day, cutoff)


@router.get("/accuracy/summary", response_model=AccuracySummaryResponse)
def read_accuracy_summary(
    days: DayRangeDep, cutoff: CutoffDep, data: WindDataDep
) -> AccuracySummaryResponse:
    """Headline accuracy of the decision-time forecast."""
    return build_accuracy_summary(data, days.first_day, days.last_day, cutoff)


@router.get("/accuracy/series", response_model=SeriesResponse)
def read_accuracy_series(days: DayRangeDep, cutoff: CutoffDep, data: WindDataDep) -> SeriesResponse:
    """Forecast against actual for every half-hour."""
    return build_series(data, days.first_day, days.last_day, cutoff)


@router.get("/accuracy/by-hour", response_model=HourlyAccuracyResponse)
def read_accuracy_by_hour(
    days: DayRangeDep, cutoff: CutoffDep, data: WindDataDep
) -> HourlyAccuracyResponse:
    """Accuracy for each UK hour of the day."""
    return build_hourly_accuracy(data, days.first_day, days.last_day, cutoff)


@router.get("/accuracy/by-day", response_model=DailyAccuracyResponse)
def read_accuracy_by_day(
    days: DayRangeDep, cutoff: CutoffDep, data: WindDataDep
) -> DailyAccuracyResponse:
    """Accuracy for each delivery day."""
    return build_daily_accuracy(data, days.first_day, days.last_day, cutoff)


@router.get("/accuracy/by-horizon", response_model=HorizonAccuracyResponse)
def read_accuracy_by_horizon(days: DayRangeDep, data: WindDataDep) -> HorizonAccuracyResponse:
    """Accuracy by forecast lead time, using every published forecast."""
    return build_horizon_accuracy(data, days.first_day, days.last_day)


@router.get("/accuracy/distribution", response_model=DistributionResponse)
def read_accuracy_distribution(
    days: DayRangeDep, cutoff: CutoffDep, data: WindDataDep
) -> DistributionResponse:
    """Histogram of decision-time errors, plus percentiles."""
    return build_distribution(data, days.first_day, days.last_day, cutoff)
