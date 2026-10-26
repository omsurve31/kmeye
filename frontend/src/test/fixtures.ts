import type { AccuracyData } from '../hooks/useAccuracyData'
import type { Decision, ErrorSummary, Meta } from '../types/api'

// Roughly the real January results, rounded, so tests read like the product.
export const errorSummaryFixture: ErrorSummary = {
  sampleCount: 1488,
  maeMw: 2042,
  rmseMw: 2509.1,
  biasMw: -1747.9,
  meanActualMw: 11284,
  normalisedMaePercent: 18.1,
  errorP5Mw: -5310,
  errorP10Mw: -4140,
  errorP50Mw: -1592,
  errorP90Mw: 544,
  errorP95Mw: 1105,
  absErrorP90Mw: 3900,
  overForecastFraction: 0.847,
}

export const metaFixture: Meta = {
  firstDeliveryDay: '2026-01-02',
  lastDeliveryDay: '2026-02-01',
  defaultCutoffTimeUk: '09:00',
  timezone: 'Europe/London',
  errorDefinition:
    'Error = actual - forecast, in MW. A negative error means the forecast was too high.',
  forecastSummary: {
    rowsFetched: 20440,
    rowsKept: 14383,
    rowsDropped: { negativeHorizon: 3697, outsideDeliveryWindow: 2360 },
  },
  actualSummary: { rowsFetched: 1488, rowsKept: 1488, rowsDropped: {} },
  missingActualHalfHours: 0,
}

export const decisionFixture: Decision = {
  deliveryDay: '2026-01-15',
  cutoffTimeUk: '09:00',
  cutoffUtc: '2026-01-14T09:00:00Z',
  forecastPublishTimesUtc: ['2026-01-14T07:30:00Z'],
  expectedTotalMwh: 23000,
  averageMw: 11500,
  peakMw: 12000,
  minimumMw: 11000,
  missingHalfHours: 0,
  points: [
    {
      startTimeUtc: '2026-01-15T00:00:00Z',
      forecastMw: 12000,
      forecastPublishTimeUtc: '2026-01-14T07:30:00Z',
      bandLowMw: 8000,
      bandHighMw: 12500,
      actualMw: 9500,
    },
    {
      startTimeUtc: '2026-01-15T00:30:00Z',
      forecastMw: 12000,
      forecastPublishTimeUtc: '2026-01-14T07:30:00Z',
      bandLowMw: 8000,
      bandHighMw: 12500,
      actualMw: 9300,
    },
    {
      startTimeUtc: '2026-01-15T01:00:00Z',
      forecastMw: 11000,
      forecastPublishTimeUtc: '2026-01-14T07:30:00Z',
      bandLowMw: 7200,
      bandHighMw: 11600,
      actualMw: 9000,
    },
    {
      startTimeUtc: '2026-01-15T01:30:00Z',
      forecastMw: 11000,
      forecastPublishTimeUtc: '2026-01-14T07:30:00Z',
      bandLowMw: null,
      bandHighMw: null,
      actualMw: null,
    },
  ],
}

export const accuracyDataFixture: AccuracyData = {
  summary: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    cutoffTimeUk: '09:00',
    summary: errorSummaryFixture,
  },
  series: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    cutoffTimeUk: '09:00',
    points: [
      { startTimeUtc: '2026-01-02T00:00:00Z', forecastMw: 12000, actualMw: 9500, errorMw: -2500 },
      { startTimeUtc: '2026-01-02T00:30:00Z', forecastMw: 12000, actualMw: 9300, errorMw: -2700 },
      { startTimeUtc: '2026-01-02T01:00:00Z', forecastMw: 11000, actualMw: 11200, errorMw: 200 },
    ],
  },
  hourly: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    cutoffTimeUk: '09:00',
    hours: [
      { hourOfDay: 0, summary: { ...errorSummaryFixture, maeMw: 2030, biasMw: -1953 } },
      { hourOfDay: 1, summary: { ...errorSummaryFixture, maeMw: 2178, biasMw: -2133 } },
    ],
  },
  daily: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    cutoffTimeUk: '09:00',
    days: [
      { deliveryDay: '2026-01-02', summary: { ...errorSummaryFixture, maeMw: 1500 } },
      { deliveryDay: '2026-01-28', summary: { ...errorSummaryFixture, maeMw: 5375 } },
    ],
  },
  distribution: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    cutoffTimeUk: '09:00',
    binWidthMw: 500,
    bins: [
      { binStartMw: -500, binEndMw: 0, count: 40 },
      { binStartMw: 0, binEndMw: 500, count: 10 },
    ],
    summary: errorSummaryFixture,
  },
  horizon: {
    firstDay: '2026-01-02',
    lastDay: '2026-02-01',
    binHours: 6,
    horizons: [
      {
        horizonStartHours: 0,
        horizonEndHours: 6,
        summary: { ...errorSummaryFixture, maeMw: 1665 },
      },
      {
        horizonStartHours: 6,
        horizonEndHours: 12,
        summary: { ...errorSummaryFixture, maeMw: 1739 },
      },
    ],
  },
}
