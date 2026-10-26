# Decisions log

One entry per decision: what was decided, alternatives, reason.

## D-001: Scope is decisions made in January 2026, so delivery days are 2 Jan – 1 Feb 2026

- **Date:** 2026-10-26
- **Decision:** The assignment says to "consider data relevant only for purchase decisions to be made in
  January 2026". Day-ahead purchases are decided the day before delivery. So decision dates are
  1–31 Jan 2026 and delivery days (target `startTime` values) are 2 Jan 00:00 UTC to
  1 Feb 2026 23:30 UTC. The decision cutoff for delivery day D falls on D-1, so every cutoff
  falls on 1–31 Jan.
- **Alternatives:** (a) Delivery days 1–31 Jan. Rejected: it would include 1 Jan, whose decision was
  made on 31 Dec 2025 (outside the scope), and it would drop 1 Feb, whose decision was made on
  31 Jan. (b) Decisions 1–31 Jan but also show 1 Jan delivery. Rejected for the same reason.
- **Reason:** It matches the assignment wording literally. The product owner confirmed it.
- **Consequences:** The date picker, API validation, tests, snapshot window and README all use
  2 Jan – 1 Feb 2026 as delivery days. Forecasts are fetched by `publishTime` from 29 Dec 2025
  (the verified maximum horizon is 66.5 hours, see `docs/DATA_NOTES.md`). Verified: Elexon has
  actuals and a pre-cutoff forecast for every delivery day in the window.

## D-002: Keep the stdlib-only exploration script and fetch the snapshot in weekly chunks

- **Date:** 2026-10-26
- **Decision:** `scripts/explore_elexon.py` uses only the Python standard library. The real ingestion
  will chunk `WINDFOR` publish windows by week even though a 123-day window worked.
- **Alternatives:** One request for the whole window (works today, 8 MB). Rejected for production
  code: the API may add limits, and chunking gives clearer errors and retries.
- **Reason:** Throwaway code should need no install. Chunking is cheap and the project rules ask for it.

## D-003: Snapshot as compact JSON or CSV, and `tzdata` as a dependency

- **Date:** 2026-10-26
- **Decision:** Plan the committed snapshot as gzip-compressed JSON or CSV (about 20,000 forecast rows
  and 1,488 actual rows). Do not use Parquet at runtime. Add `tzdata` to the backend dependencies.
- **Alternatives:** Parquet via pyarrow (smaller, typed). Rejected for now: pyarrow is large and the
  Vercel Python function limit is 250 MB unzipped. The data is only a few MB as text.
- **Reason:** Smaller deployment, simpler to explain in the video. `zoneinfo` raised
  `No time zone found with key Europe/London` on Windows without `tzdata`. To be revisited in Phase 3
  once the exact snapshot size is known.

## D-004: Align hourly forecasts to half-hourly actuals (confirmed by the product owner)

- **Date:** 2026-10-26
- **Decision:** `WINDFOR` is hourly (`startTime` on the hour) and `FUELHH` is half-hourly. Rule:
  the forecast for hour H:00 is applied to both half-hours H:00 and H:30, so the error is
  computed per half-hour and the 48 half-hours of a day are all used.
- **Alternatives:** (a) Average the two actual half-hours into one hourly actual and compare hourly
  (24 points a day, no assumption about the second half-hour). (b) Linearly interpolate the forecast
  to H:30.
- **Reason:** The assignment says both datasets share the 30-minute `startTime` axis and wants
  half-hour comparison; a step rule is simple to explain. Whether `startTime` means the start of the
  forecast hour is not stated in the API description, so the README must state this assumption.

## D-005: Phase 2 tooling choices

- **Date:** 2026-10-26
- **Decision:**
  - Frontend lint is **eslint** (typescript-eslint strict plus react-hooks), not the `oxlint` that the
    Vite template ships, because `Claude.md` requires eslint. `strict` is set explicitly in
    `tsconfig.app.json`.
  - Backend runs on **Python 3.12** in Docker and CI, and in the local virtualenv, so all three match.
    Dependencies use compatible-release ranges (`~=`) in `pyproject.toml`; `ruff` is pinned to a patch
    range because new releases change lint rules.
  - Frontend and backend are served same-origin in Docker: nginx serves the build and proxies `/api/`
    to the backend. In development Vite proxies `/api` to `localhost:8000`.
  - The `Makefile` needs GNU make, which is not installed on the Windows dev machine. CI and Linux use
    it as is; locally the same commands run directly, and the Makefile syntax was checked in a container.
  - The git identity guard (`scripts/check_identity.py`) reads personal strings from an untracked
    `.identity-blocklist`, so the strings never enter the repository.
- **Alternatives:** keep oxlint (faster, but contradicts the project rules); Python 3.14 locally
  (newer, but differs from CI); a single `uv.lock` (exact pins, one more tool to explain in the video).
- **Reason:** match `Claude.md`, keep local and CI behaviour identical, and keep the code easy to
  explain line by line.
- **Known issue:** Starlette prints a deprecation warning about its `httpx`-based test client. It is
  third-party, harmless, and the five tests pass.

## D-006: Ingestion cleaning rules and snapshot format

- **Date:** 2026-10-26
- **Decision:** `python -m app.ingest` fetches in weekly chunks and writes
  `backend/data/snapshot.json.gz` (gzip JSON, 89 KB). Rows are dropped, and counted in the snapshot,
  for these reasons, checked in this order:
  - actuals: not `WIND`, null generation, outside the delivery window, duplicate `startTime`;
  - forecasts: null generation, target hour outside the delivery window, **negative horizon**
    (published after the target hour started), duplicate `(publishTime, startTime)`.
  The first copy of a duplicate wins. A malformed row stops the run with a clear error and nothing is
  written. The file has a constant gzip header, so identical data gives identical bytes (verified by a
  second live run). Retries cover timeouts, network errors, 429 and 5xx, three attempts with doubling
  backoff.
- **Alternatives:** keep negative-horizon rows and let selection ignore them (3,697 extra rows, but they
  can never be chosen for a day-ahead cutoff); Parquet or CSV (D-003); keep the latest revision of a
  duplicate actual (no revisions were observed, so extra complexity for no data).
- **Reason:** smallest file that still supports selection, metrics and by-horizon charts, with every
  drop visible in the snapshot audit. Real run: 20,440 forecast rows fetched, 14,383 kept (3,697
  negative horizon, 2,360 outside window); 1,488 of 1,488 actual half-hours kept, none missing.
- **Consequences:** pandas is still not needed. The selection and metrics code can read the snapshot
  with `app.snapshot.read_snapshot`.
