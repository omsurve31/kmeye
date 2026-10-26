import { describe, expect, it } from 'vitest'

import {
  formatDayLabel,
  formatDayMonth,
  formatDayMonthUk,
  formatFraction,
  formatHorizonRange,
  formatHour,
  formatMw,
  formatMwh,
  formatPercent,
  formatPublishedAt,
  formatShortDate,
  formatSignedMw,
  formatThousands,
  formatTimeUk,
} from './format'

describe('formatMw', () => {
  it('rounds to whole MW with a thousands separator and the unit', () => {
    expect(formatMw(12345.6)).toBe('12,346 MW')
  })

  it('uses a real minus sign for negative values', () => {
    expect(formatMw(-1747.9)).toBe('−1,748 MW')
  })

  it('shows zero without a sign, even for a tiny negative value', () => {
    expect(formatMw(0)).toBe('0 MW')
    expect(formatMw(-0.2)).toBe('0 MW')
  })
})

describe('formatSignedMw', () => {
  it('puts a plus sign in front of positive values', () => {
    expect(formatSignedMw(544)).toBe('+544 MW')
  })

  it('puts a minus sign in front of negative values', () => {
    expect(formatSignedMw(-4140)).toBe('−4,140 MW')
  })

  it('shows zero without a sign', () => {
    expect(formatSignedMw(0)).toBe('0 MW')
  })
})

describe('formatThousands', () => {
  it('writes an axis value with a thousands separator and no unit', () => {
    expect(formatThousands(12000)).toBe('12,000')
    expect(formatThousands(-500)).toBe('−500')
    expect(formatThousands(0)).toBe('0')
  })
})

describe('formatMwh', () => {
  it('rounds to whole MWh with a thousands separator and the unit', () => {
    expect(formatMwh(278630)).toBe('278,630 MWh')
  })
})

describe('percent formatting', () => {
  it('formats a percentage with one decimal', () => {
    expect(formatPercent(18.14)).toBe('18.1%')
  })

  it('shows n/a when there is no percentage', () => {
    expect(formatPercent(null)).toBe('n/a')
  })

  it('formats a fraction between 0 and 1 as a percentage', () => {
    expect(formatFraction(0.847)).toBe('84.7%')
  })
})

describe('time and date formatting', () => {
  it('shows a UTC instant as UK winter time', () => {
    expect(formatTimeUk('2026-01-14T07:30:00Z')).toBe('07:30')
  })

  it('shows a UTC instant as UK summer time', () => {
    expect(formatTimeUk('2026-07-01T07:30:00Z')).toBe('08:30')
  })

  it('labels a delivery day with the weekday', () => {
    expect(formatDayLabel('2026-01-15')).toBe('Thu 15 Jan 2026')
  })

  it('writes a short date without the weekday', () => {
    expect(formatShortDate('2026-01-02')).toBe('2 Jan 2026')
  })

  it('describes when a forecast was published in UK time', () => {
    expect(formatPublishedAt('2026-01-14T07:30:00Z')).toBe('07:30 UK time on Wed 14 Jan 2026')
  })

  it('uses the UK date when a UTC instant falls on the next UK day in summer', () => {
    expect(formatPublishedAt('2026-07-01T23:30:00Z')).toBe('00:30 UK time on Thu 2 Jul 2026')
  })

  it('writes a delivery day as day and month', () => {
    expect(formatDayMonth('2026-01-02')).toBe('2 Jan')
  })

  it('writes the UK day and month of a UTC instant', () => {
    expect(formatDayMonthUk('2026-01-14T23:30:00Z')).toBe('14 Jan')
    expect(formatDayMonthUk('2026-07-01T23:30:00Z')).toBe('2 Jul')
  })

  it('writes an hour of the day as HH:00', () => {
    expect(formatHour(9)).toBe('09:00')
    expect(formatHour(0)).toBe('00:00')
    expect(formatHour(23)).toBe('23:00')
  })

  it('writes a forecast lead-time range in hours', () => {
    expect(formatHorizonRange(6, 12)).toBe('6–12 h')
    expect(formatHorizonRange(0, 6)).toBe('0–6 h')
  })
})
