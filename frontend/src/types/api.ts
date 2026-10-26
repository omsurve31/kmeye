// Shapes of the API responses, in camelCase. The API client is the only place that converts the
// snake_case JSON from the backend into these types.

export type DatasetSummary = {
  rowsFetched: number
  rowsKept: number
  rowsDropped: Record<string, number>
}

export type Meta = {
  firstDeliveryDay: string
  lastDeliveryDay: string
  defaultCutoffTimeUk: string
  timezone: string
  errorDefinition: string
  forecastSummary: DatasetSummary
  actualSummary: DatasetSummary
  missingActualHalfHours: number
}

// Error is actual minus forecast, in MW. Negative means the forecast was too high (the buyer is short).
export type ErrorSummary = {
  sampleCount: number
  maeMw: number
  rmseMw: number
  biasMw: number
  meanActualMw: number
  normalisedMaePercent: number | null
  errorP5Mw: number
  errorP10Mw: number
  errorP50Mw: number
  errorP90Mw: number
  errorP95Mw: number
  absErrorP90Mw: number
  overForecastFraction: number
}

export type DecisionPoint = {
  startTimeUtc: string
  forecastMw: number
  forecastPublishTimeUtc: string
  bandLowMw: number | null
  bandHighMw: number | null
  actualMw: number | null
}

export type Decision = {
  deliveryDay: string
  cutoffTimeUk: string
  cutoffUtc: string
  forecastPublishTimesUtc: string[]
  expectedTotalMwh: number
  averageMw: number
  peakMw: number
  minimumMw: number
  missingHalfHours: number
  points: DecisionPoint[]
}

export type SeriesPoint = {
  startTimeUtc: string
  forecastMw: number
  actualMw: number
  errorMw: number
}

export type AccuracyRange = {
  firstDay: string
  lastDay: string
}

export type AccuracySeries = AccuracyRange & { cutoffTimeUk: string; points: SeriesPoint[] }
export type AccuracySummary = AccuracyRange & { cutoffTimeUk: string; summary: ErrorSummary }

export type HourOfDayErrors = { hourOfDay: number; summary: ErrorSummary }
export type HourlyAccuracy = AccuracyRange & { cutoffTimeUk: string; hours: HourOfDayErrors[] }

export type DayErrors = { deliveryDay: string; summary: ErrorSummary }
export type DailyAccuracy = AccuracyRange & { cutoffTimeUk: string; days: DayErrors[] }

export type HistogramBin = { binStartMw: number; binEndMw: number; count: number }
export type Distribution = AccuracyRange & {
  cutoffTimeUk: string
  binWidthMw: number
  bins: HistogramBin[]
  summary: ErrorSummary
}

export type HorizonErrors = {
  horizonStartHours: number
  horizonEndHours: number
  summary: ErrorSummary
}
export type HorizonAccuracy = AccuracyRange & { binHours: number; horizons: HorizonErrors[] }
