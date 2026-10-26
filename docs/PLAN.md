# Phase plan

Scope (see `docs/DECISIONS.md` D-001): national UK wind, Elexon only. Decisions made 1–31 Jan 2026,
so delivery days are 2 Jan – 1 Feb 2026. Budget: 16 hours; the estimates below sum to about 15.

Each phase lists the Claude Code skills used. No commit or push happens unless requested.

## Phase 1: Verify the Elexon API and data (1.25h)
- Goal: facts before design.
- Tasks: read the OpenAPI spec; write `scripts/explore_elexon.py` with small probes; confirm
  parameter names, window limits, units, `WINDFOR` resolution and horizon, `FUELHH` `WIND` filter,
  duplicates, gaps, nulls, multiple forecasts per `startTime`; confirm forecasts and actuals exist for
  delivery days 2 Jan – 1 Feb with cutoffs on 1–31 Jan; estimate the full pull size.
- Skills: `ecc:documentation-lookup`, `ecc:search-first`, `ecc:python-patterns`,
  `ecc:architecture-decision-records`, `ecc:energy-procurement`.
- Files: `scripts/explore_elexon.py`, `docs/DATA_NOTES.md`, `docs/DECISIONS.md`.
- Done when: every item in `Claude.md` section 3 has a recorded answer and the snapshot format is
  chosen from real numbers.
- Risks: small window limits force chunking; many forecasts per target make the snapshot large.

## Phase 2: Scaffold and quality gates (1.25h)
- Tasks: backend and frontend skeletons; Makefile; `.pre-commit-config.yaml`; Dockerfiles;
  `docker-compose.yml`; `ci.yml`.
- Skills: `ecc:fastapi-patterns`, `ecc:python-testing`, `ecc:vite-patterns`, `ecc:react-testing`,
  `ecc:docker-patterns`, `ecc:git-workflow`.
- Done when: `make check` is green and `docker compose up` serves `/api/health`.

## Phase 3: Ingestion and snapshot (1.5h)
- Tasks: `elexon_client.py` (chunking, retries, timeouts); `ingest.py` (parse, filter, dedupe, UTC,
  compact snapshot); tests with mocked HTTP and fixtures.
- Skills: `superpowers:test-driven-development`, `ecc:tdd-workflow`, `ecc:python-testing`.
- Done when: tests green; snapshot built for delivery days 2 Jan – 1 Feb 2026.
- Risks: the Vercel 250 MB function limit (avoid heavy dependencies such as pyarrow at runtime).

## Phase 4: Core domain logic (2h)
- Tasks: `forecast_selection.py` (latest `publishTime` at or before the cutoff on D-1);
  `metrics.py` (MAE, RMSE, bias, normalised error, percentiles, histogram, by hour/day/horizon,
  uncertainty band); `error = actual - forecast`.
- Skills: `superpowers:test-driven-development`, `ecc:python-testing`, `ecc:python-review`.
- Done when: 100% coverage on both modules; no forecast after the cutoff can be selected.

## Phase 5: API (1.5h)
- Tasks: `/api/health`, `/api/meta`, `/api/decision`, `/api/accuracy/*`; schemas; input validation.
- Skills: `ecc:api-design`, `ecc:backend-patterns`, `ecc:fastapi-review`, `ecc:security-review`.
- Done when: every endpoint has `TestClient` tests including 4xx cases; coverage gate passes.

## Phase 6: Frontend (3.5h)
- Tasks: API client; decision view; accuracy view; loading, error and empty states.
- Skills: `ecc:react-patterns`, `ecc:frontend-patterns`, `dataviz`, `impeccable:impeccable`,
  `ecc:frontend-a11y`, `ecc:react-testing`, `ecc:react-review`, `ecc:browser-qa`.
- Done when: `make check` green, no console errors, both views usable at video resolution.

## Phase 7: Docker, CI/CD, deploy (1.5h)
- Tasks: Vercel (or Heroku fallback) deploy; `cd.yml`; post-deploy smoke test.
- Skills: `ecc:deployment-patterns`, `ecc:docker-patterns`, `ecc:github-ops`, `ecc:canary-watch`.
- Done when: live `/api/health` returns 200 and a known endpoint returns the expected schema.

## Phase 8: Docs and hardening (0.75h)
- Tasks: README with AI-tools disclosure; `FUTURE_WORK.md`; anonymity and secrets scan; diff review.
- Skills: `ecc:security-scan`, `code-review`, `superpowers:verification-before-completion`,
  `ecc:quality-gate`; agent `ecc:opensource-sanitizer`.

## Phase 9: Video and submission (1.75h)
- Tasks: `docs/VIDEO_SCRIPT.md` (5 min client pitch, 5 min tech review); record; check all links in
  incognito; submit the form.
- Skills: `ecc:ui-demo`, `ecc:code-tour`.
