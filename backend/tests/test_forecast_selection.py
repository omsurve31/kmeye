"""Tests for app/forecast_selection.py: the decision-time cutoff rule and pairing with actuals."""

from datetime import UTC, date, datetime, time

import pytest

from app.forecast_selection import (
    ForecastActualPair,
    compute_cutoff_utc,
    pair_forecasts_with_actuals,
    select_decision_forecasts,
    uk_delivery_day,
)
from app.schemas import ActualRow, ForecastRow


def _utc(month: int, day: int, hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, second, tzinfo=UTC)


def _forecast(publish: datetime, start: datetime, generation_mw: float = 1000.0) -> ForecastRow:
    return ForecastRow(publish_time_utc=publish, start_time_utc=start, generation_mw=generation_mw)


DEFAULT_CUTOFF = time(9, 0)
TARGET_JAN_15_NOON = _utc(1, 15, 12)  # delivery day 15 Jan, so the cutoff is 14 Jan 09:00


@pytest.mark.parametrize(
    ("delivery_day", "cutoff_time_uk", "expected_cutoff_utc"),
    [
        (date(2026, 1, 15), time(9, 0), _utc(1, 14, 9, 0)),
        (date(2026, 1, 2), time(9, 0), _utc(1, 1, 9, 0)),  # first delivery day
        (date(2026, 2, 1), time(9, 0), _utc(1, 31, 9, 0)),  # last delivery day
        (date(2026, 1, 15), time(0, 0), _utc(1, 14, 0, 0)),
        (date(2026, 1, 15), time(23, 30), _utc(1, 14, 23, 30)),
        (date(2026, 7, 2), time(9, 0), _utc(7, 1, 8, 0)),  # summer time: UK is UTC+1
        (date(2026, 3, 30), time(9, 0), _utc(3, 29, 8, 0)),  # day clocks went forward
    ],
)
def test_compute_cutoff_utc_is_cutoff_time_uk_on_previous_day(
    delivery_day: date, cutoff_time_uk: time, expected_cutoff_utc: datetime
) -> None:
    assert compute_cutoff_utc(delivery_day, cutoff_time_uk) == expected_cutoff_utc


def test_compute_cutoff_utc_timezone_aware_cutoff_time_raises() -> None:
    with pytest.raises(ValueError, match="timezone"):
        compute_cutoff_utc(date(2026, 1, 15), time(9, 0, tzinfo=UTC))


@pytest.mark.parametrize(
    ("target_start_utc", "expected_day"),
    [
        (_utc(1, 2, 0), date(2026, 1, 2)),
        (_utc(2, 1, 23, 30), date(2026, 2, 1)),
        (_utc(7, 1, 22, 30), date(2026, 7, 1)),  # 23:30 UK time
        (_utc(7, 1, 23, 30), date(2026, 7, 2)),  # 00:30 UK time the next day
    ],
)
def test_uk_delivery_day_uses_uk_calendar_day(
    target_start_utc: datetime, expected_day: date
) -> None:
    assert uk_delivery_day(target_start_utc) == expected_day


def test_select_decision_forecasts_picks_latest_published_before_cutoff() -> None:
    forecasts = [
        _forecast(_utc(1, 14, 4, 30), TARGET_JAN_15_NOON, 1.0),
        _forecast(_utc(1, 14, 7, 30), TARGET_JAN_15_NOON, 2.0),
        _forecast(_utc(1, 14, 9, 30), TARGET_JAN_15_NOON, 3.0),
    ]

    selected = select_decision_forecasts(forecasts, DEFAULT_CUTOFF)

    assert [(row.publish_time_utc, row.generation_mw) for row in selected] == [
        (_utc(1, 14, 7, 30), 2.0)
    ]


def test_select_decision_forecasts_publish_time_equal_to_cutoff_is_eligible() -> None:
    forecast = _forecast(_utc(1, 14, 9, 0, 0), TARGET_JAN_15_NOON)

    assert select_decision_forecasts([forecast], DEFAULT_CUTOFF) == [forecast]


def test_select_decision_forecasts_publish_one_second_after_cutoff_is_ignored() -> None:
    too_late = _forecast(_utc(1, 14, 9, 0, 1), TARGET_JAN_15_NOON, 9.0)
    on_time = _forecast(_utc(1, 14, 7, 30), TARGET_JAN_15_NOON, 2.0)

    assert select_decision_forecasts([too_late, on_time], DEFAULT_CUTOFF) == [on_time]


def test_select_decision_forecasts_only_late_forecasts_returns_nothing_for_that_target() -> None:
    too_late = _forecast(_utc(1, 14, 9, 30), TARGET_JAN_15_NOON)

    assert select_decision_forecasts([too_late], DEFAULT_CUTOFF) == []


def test_select_decision_forecasts_forecast_published_on_delivery_day_is_ignored() -> None:
    same_day = _forecast(_utc(1, 15, 6, 30), TARGET_JAN_15_NOON)

    assert select_decision_forecasts([same_day], DEFAULT_CUTOFF) == []


def test_select_decision_forecasts_result_does_not_depend_on_input_order() -> None:
    forecasts = [
        _forecast(_utc(1, 14, 4, 30), TARGET_JAN_15_NOON, 1.0),
        _forecast(_utc(1, 14, 7, 30), TARGET_JAN_15_NOON, 2.0),
        _forecast(_utc(1, 14, 9, 30), TARGET_JAN_15_NOON, 3.0),
    ]

    forward = select_decision_forecasts(forecasts, DEFAULT_CUTOFF)
    backward = select_decision_forecasts(list(reversed(forecasts)), DEFAULT_CUTOFF)

    assert forward == backward


def test_select_decision_forecasts_each_target_gets_its_own_forecast_sorted_by_target() -> None:
    later_target = _utc(1, 15, 13)
    forecasts = [
        _forecast(_utc(1, 14, 7, 30), later_target, 20.0),
        _forecast(_utc(1, 14, 7, 30), TARGET_JAN_15_NOON, 10.0),
        _forecast(_utc(1, 14, 4, 30), later_target, 19.0),
    ]

    selected = select_decision_forecasts(forecasts, DEFAULT_CUTOFF)

    assert [(row.start_time_utc, row.generation_mw) for row in selected] == [
        (TARGET_JAN_15_NOON, 10.0),
        (later_target, 20.0),
    ]


def test_select_decision_forecasts_each_delivery_day_uses_its_own_cutoff() -> None:
    jan_2_target = _utc(1, 2, 0)
    jan_3_target = _utc(1, 3, 0)
    forecasts = [
        _forecast(_utc(1, 1, 7, 30), jan_2_target, 1.0),
        _forecast(_utc(1, 1, 9, 30), jan_2_target, 2.0),  # after the 1 Jan 09:00 cutoff
        _forecast(_utc(1, 1, 9, 30), jan_3_target, 3.0),  # eligible for 3 Jan, but older
        _forecast(_utc(1, 2, 7, 30), jan_3_target, 4.0),  # the latest before 2 Jan 09:00
    ]

    selected = select_decision_forecasts(forecasts, DEFAULT_CUTOFF)

    assert [(row.start_time_utc, row.generation_mw) for row in selected] == [
        (jan_2_target, 1.0),
        (jan_3_target, 4.0),
    ]


def test_select_decision_forecasts_first_and_last_delivery_days() -> None:
    first_target = _utc(1, 2, 0)
    last_target = _utc(2, 1, 23)
    forecasts = [
        _forecast(_utc(1, 1, 7, 30), first_target, 1.0),
        _forecast(_utc(1, 1, 9, 30), first_target, 2.0),
        _forecast(_utc(1, 31, 7, 30), last_target, 3.0),
        _forecast(_utc(1, 31, 9, 30), last_target, 4.0),
    ]

    selected = select_decision_forecasts(forecasts, DEFAULT_CUTOFF)

    assert [row.generation_mw for row in selected] == [1.0, 3.0]


@pytest.mark.parametrize(
    ("cutoff_time_uk", "expected_publish_time_utc"),
    [
        (time(6, 0), _utc(1, 14, 4, 30)),
        (time(9, 0), _utc(1, 14, 7, 30)),
        (time(10, 0), _utc(1, 14, 9, 30)),
        (time(23, 0), _utc(1, 14, 22, 30)),
    ],
)
def test_select_decision_forecasts_respects_configured_cutoff(
    cutoff_time_uk: time, expected_publish_time_utc: datetime
) -> None:
    forecasts = [
        _forecast(_utc(1, 14, 4, 30), TARGET_JAN_15_NOON),
        _forecast(_utc(1, 14, 7, 30), TARGET_JAN_15_NOON),
        _forecast(_utc(1, 14, 9, 30), TARGET_JAN_15_NOON),
        _forecast(_utc(1, 14, 22, 30), TARGET_JAN_15_NOON),
    ]

    selected = select_decision_forecasts(forecasts, cutoff_time_uk)

    assert [row.publish_time_utc for row in selected] == [expected_publish_time_utc]


def test_select_decision_forecasts_cutoff_follows_uk_summer_time() -> None:
    target = _utc(7, 2, 12)  # the 09:00 UK cutoff on 1 July is 08:00 UTC
    before_cutoff = _forecast(_utc(7, 1, 7, 30), target, 1.0)
    after_cutoff = _forecast(_utc(7, 1, 8, 30), target, 2.0)  # 09:30 UK time: too late

    selected = select_decision_forecasts([before_cutoff, after_cutoff], DEFAULT_CUTOFF)

    assert selected == [before_cutoff]


def test_select_decision_forecasts_empty_input_returns_empty_list() -> None:
    assert select_decision_forecasts([], DEFAULT_CUTOFF) == []


def test_pair_forecasts_with_actuals_applies_hourly_forecast_to_both_half_hours() -> None:
    forecast = _forecast(_utc(1, 1, 7, 30), _utc(1, 2, 0), 100.0)
    actuals = [
        ActualRow(start_time_utc=_utc(1, 2, 0, 0), generation_mw=80.0),
        ActualRow(start_time_utc=_utc(1, 2, 0, 30), generation_mw=130.0),
    ]

    pairs = pair_forecasts_with_actuals([forecast], actuals)

    assert pairs == [
        ForecastActualPair(
            target_start_utc=_utc(1, 2, 0, 0),
            forecast_publish_time_utc=_utc(1, 1, 7, 30),
            horizon_hours=16.5,
            forecast_generation_mw=100.0,
            actual_generation_mw=80.0,
        ),
        ForecastActualPair(
            target_start_utc=_utc(1, 2, 0, 30),
            forecast_publish_time_utc=_utc(1, 1, 7, 30),
            horizon_hours=16.5,
            forecast_generation_mw=100.0,
            actual_generation_mw=130.0,
        ),
    ]


def test_pair_error_is_actual_minus_forecast() -> None:
    over_forecast = ForecastActualPair(
        target_start_utc=_utc(1, 2, 0),
        forecast_publish_time_utc=_utc(1, 1, 7, 30),
        horizon_hours=16.5,
        forecast_generation_mw=100.0,
        actual_generation_mw=80.0,
    )
    under_forecast = ForecastActualPair(
        target_start_utc=_utc(1, 2, 0),
        forecast_publish_time_utc=_utc(1, 1, 7, 30),
        horizon_hours=16.5,
        forecast_generation_mw=100.0,
        actual_generation_mw=130.0,
    )

    assert over_forecast.error_mw == -20.0  # forecast too high: the buyer is short
    assert under_forecast.error_mw == 30.0  # forecast too low: surplus wind


def test_pair_forecasts_with_actuals_missing_half_hour_actual_is_skipped() -> None:
    forecast = _forecast(_utc(1, 1, 7, 30), _utc(1, 2, 0), 100.0)
    actuals = [ActualRow(start_time_utc=_utc(1, 2, 0, 0), generation_mw=80.0)]

    pairs = pair_forecasts_with_actuals([forecast], actuals)

    assert [pair.target_start_utc for pair in pairs] == [_utc(1, 2, 0, 0)]


def test_pair_forecasts_with_actuals_no_actuals_returns_empty_list() -> None:
    forecast = _forecast(_utc(1, 1, 7, 30), _utc(1, 2, 0), 100.0)

    assert pair_forecasts_with_actuals([forecast], []) == []


def test_pair_forecasts_with_actuals_no_forecasts_returns_empty_list() -> None:
    actuals = [ActualRow(start_time_utc=_utc(1, 2, 0, 0), generation_mw=80.0)]

    assert pair_forecasts_with_actuals([], actuals) == []


def test_pair_forecasts_with_actuals_keeps_every_forecast_of_a_target_sorted() -> None:
    target = _utc(1, 2, 0)
    forecasts = [
        _forecast(_utc(1, 1, 9, 30), target, 110.0),
        _forecast(_utc(1, 1, 7, 30), target, 100.0),
    ]
    actuals = [ActualRow(start_time_utc=target, generation_mw=105.0)]

    pairs = pair_forecasts_with_actuals(forecasts, actuals)

    assert [(pair.forecast_publish_time_utc, pair.horizon_hours) for pair in pairs] == [
        (_utc(1, 1, 7, 30), 16.5),
        (_utc(1, 1, 9, 30), 14.5),
    ]
