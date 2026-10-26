"""Tests for the delivery window constants in app/config.py (scope decision D-001)."""

from datetime import UTC, datetime

from app.config import (
    DELIVERY_WINDOW_END_UTC,
    DELIVERY_WINDOW_START_UTC,
    FIRST_DELIVERY_DAY,
    LAST_DELIVERY_DAY,
)


def test_delivery_window_start_is_midnight_of_first_delivery_day() -> None:
    assert FIRST_DELIVERY_DAY.isoformat() == "2026-01-02"
    assert datetime(2026, 1, 2, tzinfo=UTC) == DELIVERY_WINDOW_START_UTC


def test_delivery_window_end_is_exclusive_midnight_after_last_delivery_day() -> None:
    assert LAST_DELIVERY_DAY.isoformat() == "2026-02-01"
    assert datetime(2026, 2, 2, tzinfo=UTC) == DELIVERY_WINDOW_END_UTC


def test_delivery_window_covers_31_days() -> None:
    assert (DELIVERY_WINDOW_END_UTC - DELIVERY_WINDOW_START_UTC).days == 31
