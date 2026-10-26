"""Tests for app/metrics.py. Expected values are computed by hand in the comments."""

from datetime import UTC, date, datetime

import pytest

from app.errors import NoDataError
from app.forecast_selection import ForecastActualPair
from app.metrics import (
    build_error_histogram,
    percentile,
    summarise_by_delivery_day,
    summarise_by_horizon,
    summarise_by_hour_of_day,
    summarise_errors,
)
from app.schemas import HistogramBin


def _pair(
    error_mw: float,
    actual_mw: float = 100.0,
    target_start_utc: datetime = datetime(2026, 1, 15, 0, 0, tzinfo=UTC),
    horizon_hours: float = 16.5,
) -> ForecastActualPair:
    """Build a pair whose error (actual - forecast) is exactly error_mw."""
    return ForecastActualPair(
        target_start_utc=target_start_utc,
        forecast_publish_time_utc=datetime(2026, 1, 14, 7, 30, tzinfo=UTC),
        horizon_hours=horizon_hours,
        forecast_generation_mw=actual_mw - error_mw,
        actual_generation_mw=actual_mw,
    )


# Five errors, sorted: -40, -20, 0, 10, 30. Actual is 100 MW in every pair.
FIVE_PAIRS = [_pair(error) for error in (30.0, -40.0, 0.0, 10.0, -20.0)]


def test_summarise_errors_mae_is_mean_absolute_error() -> None:
    # (40 + 20 + 0 + 10 + 30) / 5 = 20
    assert summarise_errors(FIVE_PAIRS).mae_mw == pytest.approx(20.0)


def test_summarise_errors_rmse_is_root_of_mean_squared_error() -> None:
    # (1600 + 400 + 0 + 100 + 900) / 5 = 600, and the square root of 600 is 24.4949
    assert summarise_errors(FIVE_PAIRS).rmse_mw == pytest.approx(24.494897, rel=1e-6)


def test_summarise_errors_bias_is_mean_signed_error() -> None:
    # (-40 - 20 + 0 + 10 + 30) / 5 = -4
    assert summarise_errors(FIVE_PAIRS).bias_mw == pytest.approx(-4.0)


def test_summarise_errors_normalised_mae_is_percent_of_mean_actual() -> None:
    # MAE 20 MW / mean actual 100 MW = 20 %
    summary = summarise_errors(FIVE_PAIRS)

    assert summary.mean_actual_mw == pytest.approx(100.0)
    assert summary.normalised_mae_percent == pytest.approx(20.0)


def test_summarise_errors_percentiles_use_linear_interpolation() -> None:
    # Sorted errors [-40, -20, 0, 10, 30], position = 4 * level / 100.
    # P5: position 0.2 -> -40 + 0.2 * 20 = -36
    # P10: position 0.4 -> -40 + 0.4 * 20 = -32
    # P50: position 2.0 -> 0
    # P90: position 3.6 -> 10 + 0.6 * 20 = 22
    # P95: position 3.8 -> 10 + 0.8 * 20 = 26
    summary = summarise_errors(FIVE_PAIRS)

    assert summary.error_p5_mw == pytest.approx(-36.0)
    assert summary.error_p10_mw == pytest.approx(-32.0)
    assert summary.error_p50_mw == pytest.approx(0.0)
    assert summary.error_p90_mw == pytest.approx(22.0)
    assert summary.error_p95_mw == pytest.approx(26.0)


def test_summarise_errors_over_forecast_fraction_counts_negative_errors() -> None:
    # Two of five errors are negative (-40 and -20): 0.4
    assert summarise_errors(FIVE_PAIRS).over_forecast_fraction == pytest.approx(0.4)


def test_summarise_errors_abs_error_p90_ignores_error_direction() -> None:
    # Absolute errors sorted [0, 10, 20, 30, 40]; position 3.6 -> 30 + 0.6 * 10 = 36
    assert summarise_errors(FIVE_PAIRS).abs_error_p90_mw == pytest.approx(36.0)


def test_summarise_errors_sample_count_is_number_of_pairs() -> None:
    assert summarise_errors(FIVE_PAIRS).sample_count == 5


def test_summarise_errors_forecast_above_actual_gives_negative_bias() -> None:
    pair = ForecastActualPair(
        target_start_utc=datetime(2026, 1, 15, tzinfo=UTC),
        forecast_publish_time_utc=datetime(2026, 1, 14, 7, 30, tzinfo=UTC),
        horizon_hours=16.5,
        forecast_generation_mw=100.0,
        actual_generation_mw=80.0,
    )

    summary = summarise_errors([pair])

    assert summary.bias_mw == -20.0  # error = actual - forecast = 80 - 100
    assert summary.over_forecast_fraction == 1.0


def test_summarise_errors_single_pair_has_equal_percentiles_and_rmse_equal_to_mae() -> None:
    summary = summarise_errors([_pair(-25.0)])

    assert summary.mae_mw == pytest.approx(25.0)
    assert summary.rmse_mw == pytest.approx(25.0)
    assert summary.error_p5_mw == summary.error_p95_mw == -25.0


def test_summarise_errors_perfect_forecast_has_zero_errors() -> None:
    summary = summarise_errors([_pair(0.0), _pair(0.0)])

    assert summary.mae_mw == 0.0
    assert summary.rmse_mw == 0.0
    assert summary.bias_mw == 0.0
    assert summary.over_forecast_fraction == 0.0


def test_summarise_errors_zero_mean_actual_has_no_normalised_error() -> None:
    summary = summarise_errors([_pair(0.0, actual_mw=0.0)])

    assert summary.normalised_mae_percent is None


def test_summarise_errors_empty_input_raises_no_data_error() -> None:
    with pytest.raises(NoDataError):
        summarise_errors([])


@pytest.mark.parametrize(
    ("level", "expected"),
    [(0.0, 10.0), (25.0, 17.5), (50.0, 25.0), (100.0, 40.0)],
)
def test_percentile_interpolates_between_neighbouring_values(level: float, expected: float) -> None:
    # Values [10, 20, 30, 40]: position = 3 * level / 100, e.g. 25 -> 0.75 -> 10 + 0.75 * 10
    assert percentile([10.0, 20.0, 30.0, 40.0], level) == pytest.approx(expected)


def test_percentile_single_value_returns_that_value_for_any_level() -> None:
    assert percentile([7.0], 95.0) == 7.0


def test_percentile_empty_values_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        percentile([], 50.0)


@pytest.mark.parametrize("level", [-0.1, 100.1])
def test_percentile_level_outside_0_to_100_raises(level: float) -> None:
    with pytest.raises(ValueError, match="between 0 and 100"):
        percentile([1.0, 2.0], level)


def test_build_error_histogram_groups_errors_into_bins_of_given_width() -> None:
    # Width 50: -40 and -20 fall in [-50, 0); 0, 10 and 30 fall in [0, 50).
    histogram = build_error_histogram(FIVE_PAIRS, bin_width_mw=50.0)

    assert histogram == [
        HistogramBin(bin_start_mw=-50.0, bin_end_mw=0.0, count=2),
        HistogramBin(bin_start_mw=0.0, bin_end_mw=50.0, count=3),
    ]


def test_build_error_histogram_includes_empty_bins_between_the_extremes() -> None:
    # -120 -> bin [-150, -100); 20 -> bin [0, 50). Bins [-100, -50) and [-50, 0) are empty.
    histogram = build_error_histogram([_pair(-120.0), _pair(20.0)], bin_width_mw=50.0)

    assert [(bin_.bin_start_mw, bin_.count) for bin_ in histogram] == [
        (-150.0, 1),
        (-100.0, 0),
        (-50.0, 0),
        (0.0, 1),
    ]


def test_build_error_histogram_error_on_a_bin_edge_belongs_to_the_upper_bin() -> None:
    histogram = build_error_histogram([_pair(50.0)], bin_width_mw=50.0)

    assert histogram == [HistogramBin(bin_start_mw=50.0, bin_end_mw=100.0, count=1)]


def test_build_error_histogram_empty_input_returns_empty_list() -> None:
    assert build_error_histogram([], bin_width_mw=50.0) == []


@pytest.mark.parametrize("bin_width_mw", [0.0, -50.0])
def test_build_error_histogram_non_positive_bin_width_raises(bin_width_mw: float) -> None:
    with pytest.raises(ValueError, match="bin_width_mw"):
        build_error_histogram(FIVE_PAIRS, bin_width_mw=bin_width_mw)


def _pairs_for_groups() -> list[ForecastActualPair]:
    def at(day: int, hour: int, minute: int, error_mw: float) -> ForecastActualPair:
        start = datetime(2026, 1, day, hour, minute, tzinfo=UTC)
        return _pair(error_mw, target_start_utc=start)

    return [
        at(15, 0, 0, -10.0),
        at(15, 0, 30, 10.0),
        at(16, 0, 0, 30.0),
        at(15, 1, 0, -5.0),
    ]


def test_summarise_by_hour_of_day_groups_by_uk_hour_and_sorts_by_hour() -> None:
    # Hour 0 errors [-10, 10, 30]: MAE 50 / 3, bias 30 / 3 = 10. Hour 1 error [-5]: MAE 5, bias -5.
    breakdown = summarise_by_hour_of_day(_pairs_for_groups())

    assert [group.hour_of_day for group in breakdown] == [0, 1]
    assert breakdown[0].summary.sample_count == 3
    assert breakdown[0].summary.mae_mw == pytest.approx(50.0 / 3.0)
    assert breakdown[0].summary.bias_mw == pytest.approx(10.0)
    assert breakdown[1].summary.mae_mw == pytest.approx(5.0)
    assert breakdown[1].summary.bias_mw == pytest.approx(-5.0)


def test_summarise_by_hour_of_day_uses_uk_clock_in_summer() -> None:
    summer_pair = _pair(1.0, target_start_utc=datetime(2026, 7, 1, 23, 30, tzinfo=UTC))

    breakdown = summarise_by_hour_of_day([summer_pair])

    assert [group.hour_of_day for group in breakdown] == [0]  # 00:30 UK time


def test_summarise_by_delivery_day_groups_by_uk_day_and_sorts_by_day() -> None:
    # 15 Jan errors [-10, 10, -5]: MAE 25 / 3, bias -5 / 3. 16 Jan error [30]: MAE 30.
    breakdown = summarise_by_delivery_day(_pairs_for_groups())

    assert [group.delivery_day for group in breakdown] == [date(2026, 1, 15), date(2026, 1, 16)]
    assert breakdown[0].summary.mae_mw == pytest.approx(25.0 / 3.0)
    assert breakdown[0].summary.bias_mw == pytest.approx(-5.0 / 3.0)
    assert breakdown[1].summary.mae_mw == pytest.approx(30.0)


def test_summarise_by_horizon_bins_horizons_and_puts_bin_edges_in_the_upper_bin() -> None:
    pairs = [
        _pair(1.0, horizon_hours=5.9),
        _pair(2.0, horizon_hours=6.0),
        _pair(3.0, horizon_hours=11.9),
        _pair(4.0, horizon_hours=16.5),
    ]

    breakdown = summarise_by_horizon(pairs, bin_hours=6.0)

    assert [(g.horizon_start_hours, g.horizon_end_hours) for g in breakdown] == [
        (0.0, 6.0),
        (6.0, 12.0),
        (12.0, 18.0),
    ]
    assert [g.summary.sample_count for g in breakdown] == [1, 2, 1]
    assert breakdown[1].summary.mae_mw == pytest.approx(2.5)  # errors 2 and 3


@pytest.mark.parametrize("bin_hours", [0.0, -6.0])
def test_summarise_by_horizon_non_positive_bin_hours_raises(bin_hours: float) -> None:
    with pytest.raises(ValueError, match="bin_hours"):
        summarise_by_horizon(FIVE_PAIRS, bin_hours=bin_hours)


def test_breakdowns_of_empty_input_are_empty() -> None:
    assert summarise_by_hour_of_day([]) == []
    assert summarise_by_delivery_day([]) == []
    assert summarise_by_horizon([], bin_hours=6.0) == []
