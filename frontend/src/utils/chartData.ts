import { MAX_DAY_TICKS, MAX_MW_AXIS_STEPS, NICE_MW_STEPS } from '../constants'
import type {
  DayErrors,
  DecisionPoint,
  HistogramBin,
  HorizonErrors,
  HourOfDayErrors,
  SeriesPoint,
} from '../types/api'
import { formatDayMonth, formatHorizonRange, formatHour, formatMw, formatTimeUk } from './format'

// Recharts wants flat rows with numeric x values, so each chart gets its data reshaped here
// (pure functions, easy to test) and the chart components only draw.

export type DecisionChartRow = {
  timestamp: number
  forecastMw: number
  band: [number, number] | null
  actualMw: number | null
}

export type SeriesChartRow = {
  timestamp: number
  forecastMw: number
  actualMw: number
}

export type HistogramRow = {
  label: string
  binStartMw: number
  binEndMw: number
  count: number
  // Error is actual minus forecast, so a negative error means the forecast was too high.
  direction: 'over-forecast' | 'under-forecast'
}

export type HourRow = { hour: number; label: string; maeMw: number; biasMw: number }
export type HorizonRow = { label: string; maeMw: number }
export type DayRow = { day: string; label: string; maeMw: number }

export function buildDecisionChartData(points: DecisionPoint[]): DecisionChartRow[] {
  return points.map((point) => ({
    timestamp: Date.parse(point.startTimeUtc),
    forecastMw: point.forecastMw,
    band:
      point.bandLowMw !== null && point.bandHighMw !== null
        ? [point.bandLowMw, point.bandHighMw]
        : null,
    actualMw: point.actualMw,
  }))
}

function ukClock(timestamp: number): { hour: number; minute: number } {
  const [hour = 0, minute = 0] = formatTimeUk(new Date(timestamp).toISOString())
    .split(':')
    .map(Number)
  return { hour, minute }
}

// Axis ticks on the hour (UK time), every `everyHours` hours.
export function buildTimeTicks(timestamps: number[], everyHours: number): number[] {
  return timestamps.filter((timestamp) => {
    const { hour, minute } = ukClock(timestamp)
    return minute === 0 && hour % everyHours === 0
  })
}

// One tick at UK midnight per day, thinned so a whole month does not crowd the axis.
export function buildDayTicks(timestamps: number[]): number[] {
  const midnights = timestamps.filter((timestamp) => {
    const { hour, minute } = ukClock(timestamp)
    return hour === 0 && minute === 0
  })
  const step = Math.ceil(midnights.length / MAX_DAY_TICKS)
  return midnights.filter((_timestamp, index) => index % step === 0)
}

// A MW axis from 0 up to a round number at or above `maxValue`, with a round step between ticks
// (Recharts would otherwise pick odd steps such as 5,500).
export function buildMwAxis(maxValue: number): { max: number; ticks: number[] } {
  const largestStep = NICE_MW_STEPS[NICE_MW_STEPS.length - 1] ?? 1
  const step =
    NICE_MW_STEPS.find((candidate) => Math.ceil(maxValue / candidate) <= MAX_MW_AXIS_STEPS) ??
    largestStep
  const stepCount = Math.max(1, Math.ceil(maxValue / step))
  return {
    max: stepCount * step,
    ticks: Array.from({ length: stepCount + 1 }, (_value, index) => index * step),
  }
}

export function buildSeriesChartData(points: SeriesPoint[]): SeriesChartRow[] {
  return points.map((point) => ({
    timestamp: Date.parse(point.startTimeUtc),
    forecastMw: point.forecastMw,
    actualMw: point.actualMw,
  }))
}

export function buildHistogramRows(bins: HistogramBin[]): HistogramRow[] {
  return bins.map((bin) => ({
    label: `${formatMw(bin.binStartMw)} to ${formatMw(bin.binEndMw)}`,
    binStartMw: bin.binStartMw,
    binEndMw: bin.binEndMw,
    count: bin.count,
    direction: bin.binStartMw < 0 ? 'over-forecast' : 'under-forecast',
  }))
}

export function buildHourRows(hours: HourOfDayErrors[]): HourRow[] {
  return hours.map((entry) => ({
    hour: entry.hourOfDay,
    label: formatHour(entry.hourOfDay),
    maeMw: entry.summary.maeMw,
    biasMw: entry.summary.biasMw,
  }))
}

export function buildHorizonRows(horizons: HorizonErrors[]): HorizonRow[] {
  return horizons.map((entry) => ({
    label: formatHorizonRange(entry.horizonStartHours, entry.horizonEndHours),
    maeMw: entry.summary.maeMw,
  }))
}

export function buildDayRows(days: DayErrors[]): DayRow[] {
  return days.map((entry) => ({
    day: entry.deliveryDay,
    label: formatDayMonth(entry.deliveryDay),
    maeMw: entry.summary.maeMw,
  }))
}
