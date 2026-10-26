# Claude project rules — UK Wind Forecast Portal (Full Stack SWE Challenge v4)

## 1. What we are building (and why)

A web app for the **day-ahead power buying team of a UK energy utility**. They must buy electricity one day before delivery, and wind generation is weather-dependent, so they rely on wind forecasts. The app must let them:

1. **Understand the latest wind forecast available at the moment they must decide** (decision view).
2. **Quantify how accurate those forecasts have been** (accuracy view), so they can build the error into their buying decisions.

**Scope is deliberately narrow.** National-level wind only. Elexon data only. Purchase decisions **made in January 2026** only (day-ahead, so **delivery days 2 Jan – 1 Feb 2026**). Do not add other data sources, fuel types, demand, or prices.

**This is a take-home assessment.** It is judged first by a ≤10-minute video, then by repo and README. Everything we do should serve three audiences: the client (pitch), the tech lead (review), and the evaluator (can they run and verify it quickly).

**Hard constraints from the brief**
- Frontend: **React**. Backend: **Python**. **Docker** must be used. Deployed sample app on **Vercel or Heroku**.
- Public GitHub repo with an **anonymous name** (random string, e.g. `kjhwr`).
- README must contain: file/directory guide, how to start the app, link to the deployed app, and an **explicit statement that AI tools were used**.

---

## 2. Working agreement (how Claude should work with me)

- **I must explain every line in the video.** Prefer simple, readable code over clever code. Small modules, clear names, short docstrings on non-obvious logic. No unnecessary abstraction or frameworks.
- **Plan before coding.** For each task, state the plan in a few bullets, then implement. Ask me only when a decision is genuinely ambiguous; otherwise choose the sensible default and log it.
- Before editing, inspect the working tree and relevant files. Preserve all pre-existing user changes; never overwrite, reset, clean, or revert unrelated work.
- Do not commit, push, amend, rebase, or rewrite history unless I explicitly ask. When commits are requested, make them small and focused, and ensure their tests pass first.
- **Log decisions** in `docs/DECISIONS.md` (one short entry each: decision, alternatives, reason). I will use this to prepare the tech-review part of the video.
- **Verify, don't assume.** Hit the real Elexon API and inspect real responses before writing parsing code. Never invent field names or assume resolution/units.
- When I explicitly request commits, keep them small and focused (see section 9), include the relevant tests, and keep lint and tests green before pushing.
- **Stay in scope.** If something is nice-to-have, put it in `docs/FUTURE_WORK.md` instead of building it.
- **Tests are part of the task, not a follow-up.** A task is not done until its tests exist and pass (see section 7).

---

## 3. Data sources (Elexon Insights API, no API key required)

Base URL (verify against the OpenAPI spec first): `https://data.elexon.co.uk/bmrs/api/v1`

| Purpose | Dataset | Key fields |
|---|---|---|
| Actual generation | `FUELHH` stream | `startTime` (30-min), `fuelType`, `generation` |
| Forecast generation | `WINDFOR` stream | `startTime`, `publishTime`, `generation` |

Docs from the brief:
- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream
- https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream

**First task, before any app code:** write a throwaway exploration script (`scripts/explore_elexon.py`) that:
- confirms exact query parameter names, allowed date ranges, and max window size per request (streams usually require chunking),
- confirms the response shape and units (MW),
- confirms WINDFOR's resolution (hourly vs half-hourly) and forecast horizon (how far ahead `publishTime` precedes `startTime`),
- confirms whether `FUELHH` must be filtered client-side to `fuelType == "WIND"`,
- checks for duplicates, gaps, nulls, and multiple forecasts per `startTime`.

Record findings in `docs/DATA_NOTES.md`. These findings drive the design.

**Data window.** The assignment says "purchase decisions to be made in January 2026". Each day-ahead decision is made the day before delivery, so decision dates are 1–31 Jan 2026 and **delivery days are 2 Jan – 1 Feb 2026** (targets with `startTime` from `2026-01-02T00:00Z` to `2026-02-01T23:30Z`). Forecasts for these were published before the cutoffs, so fetch `publishTime` from roughly **mid-December 2025 onward** (check actual horizon). Fetch actuals for the delivery days 2 Jan – 1 Feb 2026. Logged in `docs/DECISIONS.md`.

**Handle:** UTC vs UK local time (2 Jan – 1 Feb is winter, GMT, so equal — but still store UTC and convert explicitly at the edges), missing half-hours, duplicate rows, and API failures with retries and clear errors.

---

## 4. Core domain logic (the heart of the project — get this right and test it)

### 4.1 "Latest forecast available at decision time"
For each target half-hour `T` on delivery day `D`, the relevant forecast is the one with the **latest `publishTime` that is ≤ the decision cutoff on day D‑1**.

- The cutoff is a **configurable assumption**. Default: **09:00 UK time on D‑1**, documented clearly as an assumption (real day-ahead auction gate closures differ by venue; a single assumed cutoff keeps the analysis clean). Expose it as a setting in the backend and as a control in the UI.
- Never use a forecast published after the cutoff. This is the single most important correctness rule: using later forecasts would leak information the buyer didn't have.
- Show the user **which `publishTime` was used** for the displayed forecast.

### 4.2 Error definition
`error = actual − forecast` (MW). Be explicit in the UI and README:
- **Negative error** → forecast was too high (over-forecast) → the utility under-bought and must cover a **shortfall**, often at worse prices. This is the costly direction for the buyer.
- **Positive error** → forecast was too low → surplus wind.

### 4.3 Accuracy metrics (compute for the decision-time forecast over delivery days 2 Jan – 1 Feb 2026)
- **MAE**, **RMSE**, **bias** (mean error)
- **Normalised error** (e.g. MAE as % of mean actual generation). Avoid plain MAPE as the headline; wind output can approach zero and make it explode. If shown, explain why it's secondary.
- **Error distribution percentiles** (P5, P10, P50, P90, P95), plus histogram data
- **Breakdown by hour of day** and **by delivery day**
- **By forecast horizon** (hours between `publishTime` and `startTime`) — shows how accuracy degrades with lead time and why "latest available at decision time" matters

### 4.4 Making the error actionable
Translate the metrics into something a buyer can use: e.g. an **uncertainty band** around the forecast built from historical error percentiles (such as the P10–P90 error range for that hour of day or horizon), and a plain-language statement like *"Across January decisions, 90% of the time the outturn was within X MW of this forecast; over-forecasts exceeded Y MW in 10% of half-hours."*

Make clear in the UI and video that this is **backward-looking evidence from January 2026 decisions, not a guarantee**. Avoid overclaiming statistical precision.

---

## 5. Architecture (decided defaults; change only with a logged reason)

```
repo-root/
├── CLAUDE.md
├── README.md
├── Makefile                   # make check / test / lint / format / run
├── .pre-commit-config.yaml    # local gates (commit + push hooks)
├── docker-compose.yml         # one command to run everything locally
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml         # deps, ruff, mypy, pytest, coverage config
│   ├── app/
│   │   ├── main.py            # FastAPI app, routes, CORS
│   │   ├── config.py          # settings (cutoff time, data paths, Elexon base URL)
│   │   ├── elexon_client.py   # HTTP fetching, chunking, retries
│   │   ├── ingest.py          # fetch + clean + save snapshot
│   │   ├── forecast_selection.py  # "latest forecast before cutoff" logic
│   │   ├── metrics.py         # error metrics and aggregations
│   │   └── schemas.py         # Pydantic response models
│   ├── data/                  # committed snapshot (delivery days 2 Jan – 1 Feb 2026)
│   └── tests/                 # mirrors app/ (see section 7)
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/ (pages, components, hooks, api client, types)
├── scripts/                   # exploration + ingestion helpers
├── docs/                      # DECISIONS.md, DATA_NOTES.md, FUTURE_WORK.md, VIDEO_SCRIPT.md
└── .github/workflows/
    ├── ci.yml                 # lint + type-check + tests on every push/PR
    └── cd.yml                 # deploy, only after CI passes on main
```

**Stack choices**
- Backend: **FastAPI** + Pydantic + `httpx` + `pandas`. Typed, auto-generated OpenAPI docs (useful in the tech review).
- Frontend: **React + TypeScript (strict) + Vite**, **Recharts** (or similar simple chart lib), a small component set. Clean, professional, responsive.
- Backend tests: `pytest`, `pytest-cov`, `respx` or `pytest-httpx` (mock HTTP). Frontend tests: `vitest` + React Testing Library.
- Lint/format/types: `ruff` (lint + format) and `mypy` for Python; `eslint`, `prettier`, and `tsc --noEmit` for the frontend.

**Data strategy (important for deployment).** The scope is a fixed month, and serverless hosting has no persistent disk. So:
1. `ingest.py` pulls the Elexon data for the window and writes a **compact snapshot** (Parquet or JSON/CSV) into `backend/data/`, committed to the repo.
2. The API serves from this snapshot: fast, deterministic, and doesn't depend on Elexon being up during evaluation.
3. Keep the ingestion script runnable (`python -m app.ingest`) so the tech lead can reproduce how the snapshot was built. Optionally support a live-refresh path, but it must not be required for the app to work.

**Docker vs Vercel.** Docker is used for local/dev reproducibility and is required by the brief. Vercel doesn't run Docker images directly, so deploy the frontend as a static build and the FastAPI backend as a Vercel Python serverless function (check current Vercel Python/FastAPI docs before implementing). If that proves painful, fall back to a Heroku container deploy for the backend (frontend on Vercel, pointing at it), and log the decision. Whichever is chosen, the README must explain how Docker and the hosted deployment relate.

**API sketch** (refine as needed, keep it small)
- `GET /api/health`
- `GET /api/meta` → available delivery days, default cutoff, data coverage
- `GET /api/decision?day=2026-01-15&cutoff=09:00` → half-hourly forecast used (with `publishTime`), plus uncertainty band, plus actuals if the day is in the past
- `GET /api/accuracy/summary?from=&to=&cutoff=` → headline metrics
- `GET /api/accuracy/by-hour`, `/by-day`, `/by-horizon`, `/distribution`

---

## 6. UI / product requirements

Tone: this is a **pilot output pitched to a client**. It should look credible and polished, not like a demo script.

**View 1 — Decision view ("What will wind give us tomorrow?")**
- Date picker limited to delivery days 2 Jan – 1 Feb 2026; cutoff control (default 09:00 UK, D‑1).
- Chart: forecast wind (MW) across the day with the uncertainty band; forecast `publishTime` clearly displayed ("Based on the forecast published at …").
- Headline numbers: expected total/average/peak/minimum wind for the day.
- For past days, overlay actuals so the buyer can see how it played out.

**View 2 — Accuracy view ("How much can we trust it?")**
- KPI cards: MAE, RMSE, bias, normalised error, over-forecast tail risk.
- Charts: forecast vs actual over the selected range, error distribution, error by hour of day, error by horizon.
- A short, plain-English "what this means for buying" summary panel.

**Quality bar:** loading and error states, empty states, sensible units (MW) everywhere, accessible colours, labelled axes, no console errors, works on a laptop screen at the video's recording resolution.

---

## 7. Testing rules (mandatory)

**The rule: no backend code without tests.** Every new or changed backend function, endpoint, or module ships with tests **in the same commit**. A task is not done, and must not be committed, until its tests exist and pass.

### 7.1 Backend test requirements
- **Location and naming.** Tests live in `backend/tests/` and mirror the app structure: `app/metrics.py` → `tests/test_metrics.py`, `app/forecast_selection.py` → `tests/test_forecast_selection.py`, and so on. Test functions are named `test_<unit>_<scenario>_<expected_result>`, e.g. `test_select_forecast_publish_time_after_cutoff_is_ignored`.
- **Cover for every unit:** the happy path, edge cases (empty input, single row, zeros, nulls, missing half-hours, duplicates), boundary cases (e.g. `publishTime` exactly equal to the cutoff, first/last half-hour of the day, first/last delivery day, 2 Jan and 1 Feb), and error paths (invalid input raises the expected exception or returns the expected HTTP error).
- **Bug fixes require a regression test** that fails before the fix and passes after.
- **Mandatory tests for the core logic:**
  - Forecast selection: never returns a forecast published after the cutoff; picks the latest eligible one; handles "no eligible forecast"; handles multiple forecasts per target time; respects the configured cutoff and timezone.
  - Metrics: MAE, RMSE, bias, percentiles, normalised error, and grouped breakdowns (by hour, by day, by horizon) checked against **small hand-computed examples** written out in the test; sign convention (`actual − forecast`) is asserted explicitly.
  - Ingestion/cleaning: parsing of Elexon responses, `WIND` filtering, de-duplication, chunking of date ranges, retry behaviour on failures.
  - API: every endpoint is tested with FastAPI `TestClient` for status code, response schema, and a known-value check; also invalid parameters (bad date, delivery day outside 2 Jan – 1 Feb 2026, malformed cutoff) return a clear 4xx.
- **Tests must be deterministic and offline.** Never call the real Elexon API from tests; mock HTTP and use small fixture files in `backend/tests/fixtures/`. No dependence on the current date or time; pass timestamps explicitly. No test depends on another test's side effects or on execution order.
- For backend endpoints, also cover malformed, missing, oversized, and boundary-valued inputs; authentication failures; insufficient permissions and cross-user or cross-tenant access; not-found/conflict/rate-limit responses; downstream timeouts and unexpected responses; retries and duplicate requests where relevant; database constraints and rollback; and correct status codes, response schemas, and absence of sensitive fields.
- For security-sensitive behavior, add regression tests for vulnerabilities found. Validate untrusted input at the boundary; use parameterized database operations and safe serialization; enforce authorization server-side for each protected operation. Consider injection, mass assignment, SSRF, path traversal, replay/abuse, and denial-of-service risks where relevant. Never weaken security middleware to make tests pass.
- **Keep tests readable:** Arrange / Act / Assert, one behaviour per test, use `pytest.mark.parametrize` for input tables, shared setup in `conftest.py` fixtures.
- **Coverage gate** (enforced in CI and locally): ≥ **90%** line coverage overall on `backend/app`, and **100%** on `forecast_selection.py` and `metrics.py`. Coverage may not decrease.

### 7.2 Frontend test requirements
- Tests for the API client (request building, error handling), data-formatting helpers, and key components (decision view renders forecast + `publishTime`; accuracy view renders KPI cards; loading/error/empty states).
- Test files sit beside the code as `*.test.ts` / `*.test.tsx`. Mock the API; no network.

---

## 8. Repository rules

- **Anonymous repo.** The repo name is a random string. Before the first commit set a neutral git identity (`git config user.name "anon"`, `git config user.email "anon@example.com"`). Keep my real name, email, LinkedIn/GitHub handles, and college out of README, code, comments, package metadata (`package.json`/`pyproject.toml` author fields), Docker labels, and git history.
- **README must contain:** overview, directory/file guide, how to start (Docker command and non-Docker dev commands), how to run tests/lint, how to rebuild the data snapshot, key assumptions (cutoff, error sign convention), link to the deployed app, an **explicit AI-tools disclosure** naming the tools used, and known limitations.
- **No secrets in the repo.** Elexon is keyless. CD secrets live only in GitHub Actions secrets. Never place credentials, tokens, session identifiers, or unnecessary personal data in source, fixtures, snapshots, logs, or commits. Never log secrets; return safe client errors and keep sensitive diagnostics server-side.
- Use least privilege, safe defaults, bounded payloads, explicit timeouts, and rate limits where appropriate. Avoid revealing whether sensitive accounts or records exist.

---

## 9. Code conventions (apply to the whole codebase)

### 9.1 General
- **Language of code, comments, commits, and docs: English.** Names must be descriptive and pronounceable; no unexplained abbreviations. Prefer `forecast_publish_time_utc` over `fpt`.
- **Units and time zones go in the name or type.** Power values end in `_mw` (`actual_generation_mw`, `forecast_generation_mw`); durations in `_hours` / `_minutes`; datetimes are **timezone-aware and UTC** internally, with `_utc` or `_uk` suffix when the zone matters (`publish_time_utc`, `cutoff_time_uk`). Never use naive datetimes.
- One responsibility per function (aim for ≤ 30 lines) and per module. Pure logic (selection, metrics) is separated from I/O (HTTP, files, FastAPI).
- No dead code, no commented-out code, no stray `print`/`console.log` (use `logging` in Python). TODOs must reference an entry in `docs/FUTURE_WORK.md`.
- Comments explain **why**, not what. Every non-obvious rule (especially the cutoff logic and error sign convention) gets a short comment or docstring.
- No magic numbers: put constants and defaults in `config.py` (backend) or `constants.ts` (frontend).

### 9.2 Python (backend)
- Style: PEP 8 enforced by **ruff** (lint + format), line length **100**, imports sorted by ruff (isort rules), double quotes.
- Naming: `snake_case` for modules, functions, variables; `PascalCase` for classes and Pydantic models; `UPPER_SNAKE_CASE` for constants; `_leading_underscore` for module-private helpers. Boolean names read as questions (`is_`, `has_`, `should_`).
- **Type hints on every function signature** and return type; `mypy` runs in strict-ish mode and must pass. Use Pydantic models for all API request/response shapes; no untyped dicts crossing module boundaries.
- Docstrings (Google style) on every public function and class: one-line summary, then Args/Returns/Raises when not obvious.
- Raise specific exceptions (custom ones in a small `errors.py` if needed); never use bare `except:`. Validate inputs at the API boundary.
- API: routes are under `/api`, nouns not verbs, JSON fields in `snake_case`, ISO 8601 UTC timestamps (`2026-01-15T09:00:00Z`).

### 9.3 TypeScript / React (frontend)
- `strict` mode on; **no `any`** (use `unknown` and narrow). Prefer `type` aliases for data shapes mirroring the API.
- Naming: `PascalCase` for components, types, and their files (`DecisionView.tsx`); `camelCase` for variables, functions, hooks (hooks start with `use`, e.g. `useAccuracyData.ts`); `UPPER_SNAKE_CASE` for true constants; boolean props/vars start with `is`/`has`/`should`. Event handlers are `handleX`, handler props are `onX`.
- Function components with hooks only; one component per file; keep components small and presentational where possible, with data fetching isolated in hooks or the API client (`src/api/`).
- The API client is the **only** place that converts API `snake_case` fields into `camelCase` app types.
- Show units on every number (MW, %), format numbers/dates through shared helpers in `src/utils/format.ts`.
- Lint/format with **eslint** + **prettier**; `tsc --noEmit` must pass.

### 9.4 Files, git, and docs
- Directories and non-component files: `kebab-case` or `snake_case` consistent with the language (Python `snake_case.py`, frontend utilities `camelCase.ts`, components `PascalCase.tsx`).
- **Branching:** work on short-lived branches named `feat/<topic>`, `fix/<topic>`, `chore/<topic>`, merge to `main` via PR (even if solo) so CI runs before merge.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `ci:`), imperative mood, subject ≤ 72 chars, one logical change per commit.
- Keep `README.md` and `docs/` updated in the same commit as the change they describe.

---

## 10. Quality gates: lint, tests, CI, CD

**Principle: nothing reaches GitHub unless lint, type checks, and all tests pass. Nothing reaches production unless CI passed.** Local hooks give fast feedback; CI is the enforcing gate (hooks can be bypassed with `--no-verify`, so CI + branch protection is what actually guarantees quality). Claude must **never** bypass hooks (`--no-verify`), skip or delete failing tests, lower coverage thresholds, or add blanket lint ignores to get something through. Fix the cause.

### 10.1 One command for everything
`Makefile` targets (also what the hooks and CI call, so local and CI behave identically):
- `make lint` → `ruff check`, `ruff format --check`, `mypy` (backend); `eslint`, `prettier --check`, `tsc --noEmit` (frontend)
- `make test` → `pytest` with coverage gate (backend); `vitest run` (frontend)
- `make check` → `lint` + `test` (the full gate)
- `make format` → auto-fix formatting
- `make run` → `docker compose up --build`

### 10.2 Local hooks (pre-commit framework)
Configure `.pre-commit-config.yaml` and document `pre-commit install --hook-type pre-commit --hook-type pre-push` in the README.
- **pre-commit hook (fast):** ruff lint + format, eslint, prettier, trailing whitespace/EOF fixes, large-file and secret/identity check (block commits containing my real name/email).
- **pre-push hook (full gate):** runs `make check`. **A push is blocked if any lint error, type error, or test fails, or coverage is below the threshold.**

### 10.3 CI (`.github/workflows/ci.yml`)
Triggers on every push and every pull request.
- **Backend job:** set up Python (pinned version), cache dependencies, run ruff, mypy, pytest with the coverage gate; upload the coverage report as an artifact.
- **Frontend job:** set up Node (pinned version), cache dependencies, run eslint, prettier check, `tsc --noEmit`, vitest.
- **Docker job:** build the backend and frontend images (and run a smoke test against `/api/health`) to prove the containers actually work.
- All jobs must pass for CI to be green. Pin action versions and tool versions for reproducibility.
- **Branch protection on `main`** (configure in GitHub settings): require pull requests, require all CI status checks to pass, require branches to be up to date, no direct pushes or force pushes to `main`.

### 10.4 CD (`.github/workflows/cd.yml`)
- Runs **only on `main`**, and **only after CI succeeds** (use `workflow_run` on CI success, or a `needs:` dependency on the CI jobs in a single workflow).
- Deploys the frontend and backend to Vercel (via the Vercel CLI or Vercel's Git integration restricted to `main`), using secrets stored in GitHub Actions secrets (`VERCEL_TOKEN`, org/project IDs). If we fall back to Heroku for the backend, deploy it from the same workflow.
- After deploying, run a **post-deploy smoke test** against the live URL (`/api/health` returns 200 and a known endpoint returns the expected schema). If the smoke test fails, the workflow fails visibly.
- Preview deployments for PRs are fine, but production deploys happen only from a green `main`.

### 10.5 Definition of done (for every change)
1. Code follows section 9 conventions.
2. Tests written per section 7 and passing.
3. `make check` passes locally (lint, types, tests, coverage).
4. Docs/README/DECISIONS updated if behaviour or design changed.
5. Pushed via a branch/PR only when requested; CI green before merge.
6. Review the final diff for accidental files, debug output, commented-out code, secrets, unrelated churn, and test coverage gaps. Report the checks actually run and any residual risks or unverified behavior; never claim an unrun check passed.
