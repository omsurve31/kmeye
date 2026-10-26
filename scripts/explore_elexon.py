"""Throwaway Elexon exploration script for Phase 1. It is not part of the app.

Examples:
    python scripts/explore_elexon.py windfor 2026-01-01T00:00:00Z 2026-01-02T00:00:00Z
    python scripts/explore_elexon.py fuelhh 2026-01-02 2026-01-02
    python scripts/explore_elexon.py fuelhh 2026-01-02 2026-01-02 --all-fuels
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date, datetime, time as clock_time, timedelta, timezone

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
TIMEOUT_SECONDS = 120
SAMPLE_ROW_COUNT = 3


def fetch(path: str, params: dict[str, str]) -> list[dict]:
    """GET one endpoint and return the decoded JSON rows, printing size and timing."""
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    started = time.time()
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        body = response.read()
    print(f"GET {url}")
    print(f"  status={response.status} bytes={len(body)} seconds={time.time() - started:.1f}")
    return json.loads(body)


def parse_time(text: str) -> datetime:
    """Parse an Elexon ISO timestamp such as 2026-01-02T00:00:00Z into an aware datetime."""
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def summarise_windfor(rows: list[dict]) -> None:
    print(f"rows={len(rows)}")
    if not rows:
        return
    print("datasets:", dict(Counter(row.get("dataset") for row in rows)))
    print("null generation:", sum(row["generation"] is None for row in rows))
    publish_times = sorted({row["publishTime"] for row in rows})
    start_times = sorted({row["startTime"] for row in rows})
    print(f"distinct publishTime={len(publish_times)} first={publish_times[0]} last={publish_times[-1]}")
    print(f"distinct startTime={len(start_times)} first={start_times[0]} last={start_times[-1]}")
    pair_counts = Counter((row["publishTime"], row["startTime"]) for row in rows)
    print("duplicate (publishTime,startTime) pairs:", sum(count > 1 for count in pair_counts.values()))
    horizons_hours = [
        (parse_time(row["startTime"]) - parse_time(row["publishTime"])).total_seconds() / 3600
        for row in rows
    ]
    print(
        f"horizon hours min={min(horizons_hours):.1f} "
        f"median={statistics.median(horizons_hours):.1f} max={max(horizons_hours):.1f}"
    )
    first_publish_starts = sorted(
        parse_time(row["startTime"]) for row in rows if row["publishTime"] == publish_times[0]
    )
    steps_minutes = Counter(
        int((later - earlier).total_seconds() / 60)
        for earlier, later in zip(first_publish_starts, first_publish_starts[1:])
    )
    print("minutes between startTimes within one publish:", dict(steps_minutes))
    forecasts_per_target = Counter(row["startTime"] for row in rows).values()
    print(
        f"forecasts per startTime min={min(forecasts_per_target)} "
        f"median={statistics.median(forecasts_per_target)} max={max(forecasts_per_target)}"
    )
    print("sample rows:", rows[:SAMPLE_ROW_COUNT])


def summarise_fuelhh(rows: list[dict], from_day: date, to_day: date) -> None:
    print(f"rows={len(rows)}")
    if not rows:
        return
    print("fuel types:", dict(Counter(row["fuelType"] for row in rows)))
    wind_rows = [row for row in rows if row["fuelType"] == "WIND"]
    print(f"WIND rows={len(wind_rows)} null generation={sum(r['generation'] is None for r in wind_rows)}")
    start_counts = Counter(row["startTime"] for row in wind_rows)
    print("duplicate WIND startTime values:", sum(count > 1 for count in start_counts.values()))
    print("distinct publishTime on WIND rows:", len({row["publishTime"] for row in wind_rows}))
    expected = set()
    moment = datetime.fromisoformat(f"{from_day}T00:00:00+00:00")
    end = datetime.fromisoformat(f"{to_day}T00:00:00+00:00") + timedelta(days=1)
    while moment < end:
        expected.add(moment.strftime("%Y-%m-%dT%H:%M:%SZ"))
        moment += timedelta(minutes=30)
    missing = sorted(expected - set(start_counts))
    print(f"expected half-hours={len(expected)} missing={len(missing)} first missing={missing[:5]}")
    generations = [row["generation"] for row in wind_rows if row["generation"] is not None]
    if generations:
        print(f"WIND generation min={min(generations)} max={max(generations)}")
    print("sample WIND rows:", wind_rows[:SAMPLE_ROW_COUNT])


def check_decision_coverage(forecast_rows: list[dict], wind_rows: list[dict]) -> None:
    """For each delivery day, check actuals and a forecast published by 09:00 on D-1.

    UK time equals UTC from 26 Oct 2025 to 28 Mar 2026 (GMT), so the 09:00 UK cutoff is 09:00 UTC.
    """
    actual_counts = Counter(parse_time(row["startTime"]).date() for row in wind_rows)
    publish_times_by_target = defaultdict(list)
    for row in forecast_rows:
        publish_times_by_target[parse_time(row["startTime"])].append(parse_time(row["publishTime"]))
    day = date(2026, 1, 2)
    while day <= date(2026, 2, 1):
        cutoff = datetime.combine(day - timedelta(days=1), clock_time(9), tzinfo=timezone.utc)
        midnight = datetime.combine(day, clock_time(0), tzinfo=timezone.utc)
        horizons, used_publish_times, missing_targets = [], set(), 0
        for hour in range(24):
            target = midnight + timedelta(hours=hour)
            eligible = [p for p in publish_times_by_target.get(target, []) if p <= cutoff]
            if not eligible:
                missing_targets += 1
                continue
            used = max(eligible)
            used_publish_times.add(used)
            horizons.append((target - used).total_seconds() / 3600)
        horizon_text = f"{min(horizons):.1f}-{max(horizons):.1f}h" if horizons else "n/a"
        print(
            f"D={day} cutoff={cutoff:%Y-%m-%dT%H:%MZ} actual_half_hours={actual_counts[day]}/48 "
            f"hourly_targets_with_forecast={24 - missing_targets}/24 horizon={horizon_text} "
            f"distinct_publish_times_used={len(used_publish_times)}"
        )
        day += timedelta(days=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    windfor = sub.add_parser("windfor")
    windfor.add_argument("publish_from")
    windfor.add_argument("publish_to")
    fuelhh = sub.add_parser("fuelhh")
    fuelhh.add_argument("settlement_from")
    fuelhh.add_argument("settlement_to")
    fuelhh.add_argument("--all-fuels", action="store_true")
    sub.add_parser("coverage", help="check delivery days 2 Jan - 1 Feb 2026 against D-1 09:00 cutoffs")
    for command in (windfor, fuelhh):
        command.add_argument("--save", help="write the raw JSON rows to this path")
    args = parser.parse_args()

    try:
        if args.command == "coverage":
            forecast_rows = fetch(
                "/datasets/WINDFOR/stream",
                {"publishDateTimeFrom": "2025-12-29T00:00:00Z", "publishDateTimeTo": "2026-01-31T09:00:00Z"},
            )
            wind_rows = fetch(
                "/datasets/FUELHH/stream",
                {"settlementDateFrom": "2026-01-02", "settlementDateTo": "2026-02-01", "fuelType": "WIND"},
            )
            check_decision_coverage(forecast_rows, wind_rows)
            return 0
        if args.command == "windfor":
            params = {"publishDateTimeFrom": args.publish_from, "publishDateTimeTo": args.publish_to}
            rows = fetch("/datasets/WINDFOR/stream", params)
            summarise_windfor(rows)
        else:
            params = {"settlementDateFrom": args.settlement_from, "settlementDateTo": args.settlement_to}
            if not args.all_fuels:
                params["fuelType"] = "WIND"
            rows = fetch("/datasets/FUELHH/stream", params)
            summarise_fuelhh(
                rows, date.fromisoformat(args.settlement_from), date.fromisoformat(args.settlement_to)
            )
    except urllib.error.HTTPError as error:
        print(f"HTTP {error.code}: {error.read()[:500]!r}")
        return 1
    if args.save:
        with open(args.save, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
    return 0


if __name__ == "__main__":
    sys.exit(main())
