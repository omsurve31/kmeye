# Future work

Nice-to-have items that are out of scope for the pilot. TODO comments in code must point here.

## Analysis

- **Out-of-sample uncertainty band.** The band shown in the decision view is built from the P10 and
  P90 errors of all January data, including the day being shown. A leave-one-day-out band would be a
  fairer test of how the band performs on a new day.
- **Explain the -1.7 GW bias.** Check how the WINDFOR forecast and the FUELHH wind outturn are defined
  (embedded wind, curtailment, constraints) before presenting the bias as forecaster error.
- **Other alignments of hourly forecasts to half-hourly actuals** (D-004): average the actuals to
  hourly, or interpolate the forecast.
- **Other decision cutoffs per market** and a cutoff sweep chart.

## Platform

- **Live refresh** of the snapshot from Elexon behind an admin-only endpoint.
- **Update GitHub Actions versions.** CI warns that `actions/checkout`, `setup-node`, `setup-python`
  and `upload-artifact` at the pinned versions run on the deprecated Node 20 runtime.
