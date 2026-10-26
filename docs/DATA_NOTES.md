# Elexon data notes (Phase 1 findings)

Verified on 2026-10-26 against the live Elexon Insights API with `scripts/explore_elexon.py`
(stdlib only, throwaway). Scope: delivery days 2 Jan – 1 Feb 2026, decision cutoffs 1–31 Jan 2026
(see `docs/DECISIONS.md` D-001).

## Endpoints and parameters

Base URL `https://data.elexon.co.uk/bmrs/api/v1` (from the OpenAPI spec at
`https://data.elexon.co.uk/swagger/v1/swagger.json`). No API key. Responses are a JSON array of rows.

| Dataset | Path | Filter parameters |
|---|---|---|
| Actuals | `/datasets/FUELHH/stream` | `settlementDateFrom`, `settlementDateTo` (`yyyy-MM-dd`), `settlementPeriod`, `fuelType`; or `publishDateTimeFrom/To` (settlement dates cannot be combined with publish dates) |
| Forecasts | `/datasets/WINDFOR/stream` | `publishDateTimeFrom`, `publishDateTimeTo` only. There is no startTime filter. Without a filter it returns only the latest forecast |

## Response fields

- `FUELHH` row: `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`,
  `fuelType`, `generation` (integer, average MW over the half-hour).
- `WINDFOR` row: `dataset`, `publishTime`, `startTime`, `generation` (integer MW).
- All timestamps are ISO 8601 UTC with a `Z` suffix.

## Findings

Actuals (`FUELHH`)
- `fuelType=WIND` works server-side (48 rows for one day). Without it the API returns 20 fuel types
  (960 rows per day). We still filter `fuelType == "WIND"` client-side as a cheap guard.
- Resolution is 30 minutes. For 2 Jan – 1 Feb 2026 the response had 1488 rows = 31 x 48, so **no
  missing half-hours**, no duplicate `startTime`, no null `generation`.
- Wind generation ranged from 1695 to 17805 MW in that window.
- `publishTime` of an actual row is normally `startTime + 30 min`. Four rows were published late
  (gaps of 56 to 145 minutes around 15 Jan) and two rows share `2026-01-15T12:26:00Z`. This does not
  affect us because we do not use `publishTime` of actuals.

Forecasts (`WINDFOR`)
- Resolution is **hourly**: every `startTime` is on the hour, consecutive `startTime` values within
  one publish are 60 minutes apart. Actuals are half-hourly, so the two need aligning (D-004).
- A forecast is published **8 times a day**, at 02:30, 04:30, 07:30, 09:30, 11:30, 15:30, 18:30 and
  22:30 UTC (once, on one day in the 35-day sample, 12:25 instead of 11:30).
- Each publish covers 73 hourly targets, from about 25 hours in the past to **66.5 hours ahead**.
  Rows with a negative horizon are forecasts for hours that already started and are not relevant to a
  day-ahead decision.
- Horizon (`startTime - publishTime`) ranges from -27.5 h to +66.5 h. Every target has 8 to 32
  forecasts in a 35-day pull, median 24.
- No duplicate `(publishTime, startTime)` pairs and no null `generation` in any window tried.
- Wind forecast values ranged from 2250 to 21353 MW (35-day window).

Request limits and size
- No window limit was hit: a 123-day `WINDFOR` publish window (71,856 rows, 8.1 MB) returned in
  4 seconds. We still plan to chunk by week for robustness and clear error handling (D-002).
- 35 days of `WINDFOR` (publish 29 Dec 2025 – 1 Feb 2026) is 20,440 rows, about 2.4 MB of JSON.
  Actuals for the delivery window are about 0.27 MB.

## Decision-cutoff coverage check

`python scripts/explore_elexon.py coverage` fetches `WINDFOR` published 29 Dec 2025 – 31 Jan 2026
09:00 UTC and `FUELHH` WIND for 2 Jan – 1 Feb, then checks every delivery day D with the cutoff
09:00 on D-1 (UK time equals UTC in this period).

Result for all 31 delivery days (2 Jan to 1 Feb), cutoffs 1 Jan to 31 Jan:
- Actuals: 48 of 48 half-hours.
- Forecast: 24 of 24 hourly targets have a forecast published at or before the cutoff.
- The forecast used is always the **07:30 UTC publish of D-1** (horizon 16.5 to 39.5 hours). The next
  publish, 09:30, falls 30 minutes after the default cutoff, so a later cutoff would change the
  forecast. This makes the cutoff control meaningful in the UI.

## Consequences for the design

- Snapshot window: `WINDFOR` published 29 Dec 2025 00:00 UTC to 2 Feb 2026 00:00 UTC, kept only for
  target `startTime` within 2 Jan – 1 Feb 2026; `FUELHH` WIND for the same targets. The earliest
  useful publish is about 30 Dec (66.5 h before 2 Jan 00:00).
- `tzdata` is needed: Python's `zoneinfo` fails on Windows without it (`No time zone found with
  key Europe/London`). It must be a backend dependency (D-003).
- Rows with a negative horizon are dropped or ignored by the selection step, never used.
