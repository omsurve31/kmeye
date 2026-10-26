import { UK_TIMEZONE } from '../constants'

const MINUS_SIGN = '−'
const UTC_TIMEZONE = 'UTC'
const PERCENT_SCALE = 100

const wholeNumberFormat = new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 })
const oneDecimalFormat = new Intl.NumberFormat('en-GB', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})
const ukTimeFormat = new Intl.DateTimeFormat('en-GB', {
  timeZone: UK_TIMEZONE,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
})

function roundToWhole(value: number): number {
  // Adding 0 turns -0 into 0, so a tiny negative value never shows as "-0".
  return Math.round(value) + 0
}

function formatWhole(value: number): string {
  const rounded = roundToWhole(value)
  const digits = wholeNumberFormat.format(Math.abs(rounded))
  return rounded < 0 ? `${MINUS_SIGN}${digits}` : digits
}

export function formatMw(value: number): string {
  return `${formatWhole(value)} MW`
}

export function formatSignedMw(value: number): string {
  const rounded = roundToWhole(value)
  return rounded > 0 ? `+${formatWhole(rounded)} MW` : formatMw(rounded)
}

export function formatMwh(value: number): string {
  return `${formatWhole(value)} MWh`
}

export function formatPercent(value: number | null): string {
  return value === null ? 'n/a' : `${oneDecimalFormat.format(value)}%`
}

// A share between 0 and 1, shown as a percentage.
export function formatFraction(fraction: number): string {
  return formatPercent(fraction * PERCENT_SCALE)
}

export function formatTimeUk(isoUtc: string): string {
  return ukTimeFormat.format(new Date(isoUtc))
}

function describeDate(instant: Date, timeZone: string, shouldIncludeWeekday: boolean): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone,
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).formatToParts(instant)
  const part = (type: Intl.DateTimeFormatPartTypes): string =>
    parts.find((candidate) => candidate.type === type)?.value ?? ''
  const date = `${part('day')} ${part('month')} ${part('year')}`
  return shouldIncludeWeekday ? `${part('weekday')} ${date}` : date
}

// A delivery day such as "2026-01-15" has no time of day; noon UTC keeps it on the same date.
function noonUtc(day: string): Date {
  return new Date(`${day}T12:00:00Z`)
}

export function formatDayLabel(day: string): string {
  return describeDate(noonUtc(day), UTC_TIMEZONE, true)
}

export function formatShortDate(day: string): string {
  return describeDate(noonUtc(day), UTC_TIMEZONE, false)
}

// "2 Jan 2026" without the year.
function withoutYear(date: string): string {
  return date.slice(0, date.lastIndexOf(' '))
}

export function formatDayMonth(day: string): string {
  return withoutYear(describeDate(noonUtc(day), UTC_TIMEZONE, false))
}

export function formatDayMonthUk(isoUtc: string): string {
  return withoutYear(describeDate(new Date(isoUtc), UK_TIMEZONE, false))
}

// A bare number with a thousands separator, for chart axes where the unit is in the axis label.
export function formatThousands(value: number): string {
  return formatWhole(value)
}

export function formatPublishedAt(isoUtc: string): string {
  const date = describeDate(new Date(isoUtc), UK_TIMEZONE, true)
  return `${formatTimeUk(isoUtc)} UK time on ${date}`
}

export function formatHour(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`
}

export function formatHorizonRange(startHours: number, endHours: number): string {
  return `${startHours}–${endHours} h`
}
