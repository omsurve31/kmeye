import type { ErrorSummary } from '../types/api'
import { formatFraction, formatMw, formatShortDate } from './format'

export type SummaryContext = {
  firstDay: string
  lastDay: string
  cutoffTimeUk: string
}

export function describeBias(biasMw: number): string {
  const rounded = Math.round(biasMw)
  if (rounded === 0) {
    return 'On average the forecast matched the outturn.'
  }
  const direction = rounded < 0 ? 'higher' : 'lower'
  return `On average the forecast was ${formatMw(Math.abs(rounded))} ${direction} than the outturn.`
}

// Error is actual minus forecast, so a negative 10th percentile is the size of a shortfall that
// happened in at least 10% of half-hours.
function describeOverForecast(summary: ErrorSummary): string {
  const share = formatFraction(summary.overForecastFraction)
  if (summary.errorP10Mw >= 0) {
    return `The forecast was too high in only ${share} of half-hours.`
  }
  return (
    `The forecast was too high in ${share} of half-hours. In 10% of half-hours it was too high by ` +
    `more than ${formatMw(-summary.errorP10Mw)}, a shortfall the buyer would have had to cover.`
  )
}

// The "what this means for buying" sentences. They describe January only: no guarantee.
export function buildBuyingSummary(summary: ErrorSummary, context: SummaryContext): string[] {
  const first = formatShortDate(context.firstDay)
  const last = formatShortDate(context.lastDay)
  return [
    `In 90% of half-hours between ${first} and ${last}, the actual outturn finished within ` +
      `${formatMw(summary.absErrorP90Mw)} of the forecast available at the ` +
      `${context.cutoffTimeUk} UK cutoff.`,
    describeOverForecast(summary),
    describeBias(summary.biasMw),
    'This is backward-looking evidence from January 2026 decisions, not a guarantee of future accuracy.',
  ]
}
