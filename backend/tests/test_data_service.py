"""Tests for app/data_service.py: building API responses from the snapshot.

Expected values are worked out by hand from the fixture in conftest.py. At the 09:00 cutoff the
errors (actual - forecast) are 2 Jan: -100, +100, +200, -200 and 3 Jan: +300, -300, -100, +300.
"""

from collections.abc import Callable
from datetime import UTC, date, datetime, time

import pytest

from app.config import MAX_CACHED_CUTOFFS
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
    pairs_in_range,
)
from app.errors import NoDataError
from app.schemas import ActualRow, ForecastRow

DEFAULT_CUTOFF = time(9, 0)
JAN_2 = date(2026, 1, 2)
JAN_3 = date(2026, 1, 3)
MakeWindData = Callable[[list[ForecastRow], list[ActualRow]], WindData]


def _utc(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2026, month, day, hour, minute, tzinfo=UTC)


def test_wind_data_decision_forecasts_are_cached_per_cutoff(wind_data: WindData) -> None:
    first = wind_data.decision_forecasts(DEFAULT_CUTOFF)

    assert len(first) == 4
    assert wind_data.decision_forecasts(DEFAULT_CUTOFF) is first


def test_wind_data_decision_pairs_cover_each_half_hour_once(wind_data: WindData) -> None:
    assert len(wind_data.decision_pairs(DEFAULT_CUTOFF)) == 8


def test_wind_data_later_cutoff_selects_later_forecasts(wind_data: WindData) -> None:
    pairs = wind_data.decision_pairs(time(10, 0))

    assert sorted({pair.forecast_publish_time_utc.hour for pair in pairs}) == [9]


def test_wind_data_cache_is_bounded_so_a_client_cannot_use_up_memory(wind_data: WindData) -> None:
    # Regression: a client chooses the cutoff, and every new one used to be cached forever.
    for minute in range(MAX_CACHED_CUTOFFS + 8):
        wind_data.hour_bands(time(10, minute))

    assert wind_data.cached_cutoff_count == MAX_CACHED_CUTOFFS


def test_wind_data_evicted_cutoff_is_recomputed_with_the_same_result(wind_data: WindData) -> None:
    first = wind_data.decision_pairs(time(10, 0))
    for minute in range(1, MAX_CACHED_CUTOFFS + 1):
        wind_data.decision_pairs(time(10, minute))  # pushes 10:00 out of the cache

    again = wind_data.decision_pairs(time(10, 0))

    assert again == first
    assert again is not first


def test_wind_data_all_pairs_include_every_published_forecast(wind_data: WindData) -> None:
    assert len(wind_data.all_pairs()) == 16


def test_build_meta_describes_window_assumptions_and_audit(wind_data: WindData) -> None:
    meta = build_meta(wind_data)

    assert (meta.first_delivery_day, meta.last_delivery_day) == (date(2026, 1, 2), date(2026, 2, 1))
    assert meta.default_cutoff_time_uk == "09:00"
    assert meta.timezone == "Europe/London"
    assert "actual - forecast" in meta.error_definition
    assert meta.forecast_summary.rows_kept == 8
    assert meta.actual_summary.rows_kept == 8
    assert meta.missing_actual_half_hours == 1480


def test_build_decision_returns_forecast_used_with_publish_time_and_actuals(
    wind_data: WindData,
) -> None:
    decision = build_decision(wind_data, JAN_2, DEFAULT_CUTOFF)

    assert decision.delivery_day == JAN_2
    assert decision.cutoff_time_uk == "09:00"
    assert decision.cutoff_utc == _utc(1, 1, 9, 0)
    assert decision.forecast_publish_times_utc == [_utc(1, 1, 7, 30)]
    assert [point.start_time_utc for point in decision.points] == [
        _utc(1, 2, 0, 0),
        _utc(1, 2, 0, 30),
        _utc(1, 2, 1, 0),
        _utc(1, 2, 1, 30),
    ]
    assert [point.forecast_mw for point in decision.points] == [1000.0, 1000.0, 2000.0, 2000.0]
    assert [point.actual_mw for point in decision.points] == [900.0, 1100.0, 2200.0, 1800.0]
    assert {point.forecast_publish_time_utc for point in decision.points} == {_utc(1, 1, 7, 30)}


def test_build_decision_band_is_forecast_plus_p10_and_p90_error_of_the_same_hour(
    wind_data: WindData,
) -> None:
    # Hour 00 errors sorted [-300, -100, 100, 300]:
    #   P10 = -300 + 0.3 * 200 = -240 and P90 = 100 + 0.7 * 200 = 240.
    # Hour 01 errors sorted [-200, -100, 200, 300]:
    #   P10 = -200 + 0.3 * 100 = -170 and P90 = 200 + 0.7 * 100 = 270.
    points = build_decision(wind_data, JAN_2, DEFAULT_CUTOFF).points

    assert points[0].band_low_mw == pytest.approx(760.0)
    assert points[0].band_high_mw == pytest.approx(1240.0)
    assert points[2].band_low_mw == pytest.approx(1830.0)
    assert points[2].band_high_mw == pytest.approx(2270.0)


def test_build_decision_headline_numbers_are_hand_computed(wind_data: WindData) -> None:
    decision = build_decision(wind_data, JAN_2, DEFAULT_CUTOFF)

    # Half-hour forecasts [1000, 1000, 2000, 2000] MW, each lasting 0.5 h.
    assert decision.expected_total_mwh == pytest.approx(3000.0)
    assert decision.average_mw == pytest.approx(1500.0)
    assert decision.peak_mw == 2000.0
    assert decision.minimum_mw == 1000.0
    assert decision.missing_half_hours == 44  # 48 half-hours in a day, 4 have a forecast


def test_build_decision_later_cutoff_uses_the_later_forecast(wind_data: WindData) -> None:
    decision = build_decision(wind_data, JAN_2, time(10, 0))

    assert decision.forecast_publish_times_utc == [_utc(1, 1, 9, 30)]
    assert [point.forecast_mw for point in decision.points] == [1100.0, 1100.0, 2100.0, 2100.0]
    assert decision.average_mw == pytest.approx(1600.0)


def test_build_decision_day_without_a_forecast_raises_no_data_error(wind_data: WindData) -> None:
    with pytest.raises(NoDataError, match="2026-01-10"):
        build_decision(wind_data, date(2026, 1, 10), DEFAULT_CUTOFF)


def test_build_decision_cutoff_before_every_publish_raises_no_data_error(
    wind_data: WindData,
) -> None:
    with pytest.raises(NoDataError):
        build_decision(wind_data, JAN_2, time(7, 0))


def test_build_decision_band_is_never_below_zero_mw(make_wind_data: MakeWindData) -> None:
    # Hour 00 errors [-500, -50] give P10 = -455 and P90 = -95, so 50 + P10 would be below zero.
    forecasts = [
        ForecastRow(
            publish_time_utc=_utc(1, 1, 7, 30), start_time_utc=_utc(1, 2, 0), generation_mw=50.0
        ),
        ForecastRow(
            publish_time_utc=_utc(1, 2, 7, 30), start_time_utc=_utc(1, 3, 0), generation_mw=500.0
        ),
    ]
    actuals = [
        ActualRow(start_time_utc=_utc(1, 2, 0), generation_mw=0.0),
        ActualRow(start_time_utc=_utc(1, 3, 0), generation_mw=0.0),
    ]

    point = build_decision(make_wind_data(forecasts, actuals), JAN_2, DEFAULT_CUTOFF).points[0]

    assert point.band_low_mw == 0.0
    assert point.band_high_mw == 0.0


def test_build_decision_hour_without_error_history_has_no_band_and_no_actual(
    make_wind_data: MakeWindData,
) -> None:
    forecast = ForecastRow(
        publish_time_utc=_utc(1, 1, 7, 30), start_time_utc=_utc(1, 2, 0), generation_mw=800.0
    )

    point = build_decision(make_wind_data([forecast], []), JAN_2, DEFAULT_CUTOFF).points[0]

    assert (point.band_low_mw, point.band_high_mw, point.actual_mw) == (None, None, None)
    assert point.forecast_mw == 800.0


def test_pairs_in_range_includes_both_end_days(wind_data: WindData) -> None:
    pairs = wind_data.decision_pairs(DEFAULT_CUTOFF)

    assert len(pairs_in_range(pairs, JAN_2, JAN_3)) == 8
    assert len(pairs_in_range(pairs, JAN_3, JAN_3)) == 4
    assert pairs_in_range(pairs, date(2026, 1, 4), date(2026, 1, 9)) == []


def test_build_series_lists_forecast_actual_and_error_per_half_hour(wind_data: WindData) -> None:
    series = build_series(wind_data, JAN_2, JAN_2, DEFAULT_CUTOFF)

    assert (series.first_day, series.last_day, series.cutoff_time_uk) == (JAN_2, JAN_2, "09:00")
    assert [point.error_mw for point in series.points] == [-100.0, 100.0, 200.0, -200.0]
    assert [point.actual_mw for point in series.points] == [900.0, 1100.0, 2200.0, 1800.0]
    assert [point.forecast_mw for point in series.points] == [1000.0, 1000.0, 2000.0, 2000.0]


def test_build_accuracy_summary_whole_range_matches_hand_computed_values(
    wind_data: WindData,
) -> None:
    # Errors [-100, 100, 200, -200, 300, -300, -100, 300]:
    # MAE = 1600 / 8 = 200, bias = 200 / 8 = 25, RMSE = sqrt(380000 / 8) = 217.94,
    # mean actual = 20200 / 8 = 2525, so normalised MAE = 7.92 %,
    # 4 of 8 errors are negative, absolute errors sorted [100, 100, 100, 200, 200, 300, 300, 300]
    # so P90 = 300.
    summary = build_accuracy_summary(wind_data, JAN_2, JAN_3, DEFAULT_CUTOFF).summary

    assert summary.sample_count == 8
    assert summary.mae_mw == pytest.approx(200.0)
    assert summary.bias_mw == pytest.approx(25.0)
    assert summary.rmse_mw == pytest.approx(217.944, rel=1e-4)
    assert summary.mean_actual_mw == pytest.approx(2525.0)
    assert summary.normalised_mae_percent == pytest.approx(7.9208, rel=1e-4)
    assert summary.over_forecast_fraction == pytest.approx(0.5)
    assert summary.abs_error_p90_mw == pytest.approx(300.0)


def test_build_accuracy_summary_single_day_only_uses_that_day(wind_data: WindData) -> None:
    summary = build_accuracy_summary(wind_data, JAN_2, JAN_2, DEFAULT_CUTOFF).summary

    assert summary.sample_count == 4
    assert summary.mae_mw == pytest.approx(150.0)
    assert summary.bias_mw == pytest.approx(0.0)


def test_build_accuracy_summary_range_without_data_raises_no_data_error(
    wind_data: WindData,
) -> None:
    with pytest.raises(NoDataError, match="selected days"):
        build_accuracy_summary(wind_data, date(2026, 1, 10), date(2026, 1, 10), DEFAULT_CUTOFF)


def test_build_hourly_accuracy_has_one_entry_per_hour_with_data(wind_data: WindData) -> None:
    hours = build_hourly_accuracy(wind_data, JAN_2, JAN_3, DEFAULT_CUTOFF).hours

    assert [entry.hour_of_day for entry in hours] == [0, 1]
    assert hours[0].summary.mae_mw == pytest.approx(200.0)  # (100 + 100 + 300 + 300) / 4
    assert hours[1].summary.mae_mw == pytest.approx(200.0)  # (200 + 200 + 100 + 300) / 4


def test_build_daily_accuracy_has_one_entry_per_delivery_day(wind_data: WindData) -> None:
    days = build_daily_accuracy(wind_data, JAN_2, JAN_3, DEFAULT_CUTOFF).days

    assert [entry.delivery_day for entry in days] == [JAN_2, JAN_3]
    assert days[0].summary.mae_mw == pytest.approx(150.0)
    assert days[1].summary.mae_mw == pytest.approx(250.0)  # (300 + 300 + 100 + 300) / 4


def test_build_horizon_accuracy_uses_every_published_forecast(wind_data: WindData) -> None:
    # Horizons are 16.5, 17.5 (07:30 forecasts) and 14.5, 15.5 (09:30 forecasts): all in [12, 18).
    response = build_horizon_accuracy(wind_data, JAN_2, JAN_3)

    assert response.bin_hours == 6.0
    assert [(h.horizon_start_hours, h.horizon_end_hours) for h in response.horizons] == [
        (12.0, 18.0)
    ]
    assert response.horizons[0].summary.sample_count == 16


def test_build_distribution_counts_errors_in_500_mw_bins(wind_data: WindData) -> None:
    response = build_distribution(wind_data, JAN_2, JAN_3, DEFAULT_CUTOFF)

    # Four negative errors fall in [-500, 0), four non-negative ones in [0, 500).
    assert response.bin_width_mw == 500.0
    assert [(b.bin_start_mw, b.bin_end_mw, b.count) for b in response.bins] == [
        (-500.0, 0.0, 4),
        (0.0, 500.0, 4),
    ]
    assert response.summary.sample_count == 8
