import { describe, expect, it } from 'vitest'

import { accuracyDataFixture, decisionFixture } from '../test/fixtures'
import {
  buildDayRows,
  buildDayTicks,
  buildDecisionChartData,
  buildHistogramRows,
  buildHorizonRows,
  buildHourRows,
  buildMwAxis,
  buildSeriesChartData,
  buildTimeTicks,
} from './chartData'

const HALF_HOUR_MS = 30 * 60 * 1000

function halfHourTimestamps(startIso: string, count: number): number[] {
  const start = Date.parse(startIso)
  return Array.from({ length: count }, (_value, index) => start + index * HALF_HOUR_MS)
}

describe('buildDecisionChartData', () => {
  it('turns a point into a row with a numeric timestamp and a [low, high] band', () => {
    const [row] = buildDecisionChartData(decisionFixture.points)

    expect(row).toEqual({
      timestamp: Date.parse('2026-01-15T00:00:00Z'),
      forecastMw: 12000,
      band: [8000, 12500],
      actualMw: 9500,
    })
  })

  it('uses null for a missing band and a missing actual', () => {
    const rows = buildDecisionChartData(decisionFixture.points)

    expect(rows[3]).toMatchObject({ band: null, actualMw: null })
  })
})

describe('buildTimeTicks', () => {
  it('picks every third UK hour on the hour across one day', () => {
    const ticks = buildTimeTicks(halfHourTimestamps('2026-01-15T00:00:00Z', 48), 3)

    expect(ticks).toHaveLength(8)
    expect(ticks[0]).toBe(Date.parse('2026-01-15T00:00:00Z'))
    expect(ticks[7]).toBe(Date.parse('2026-01-15T21:00:00Z'))
  })

  it('follows UK clock time, not UTC, in summer', () => {
    const ticks = buildTimeTicks(halfHourTimestamps('2026-07-01T00:00:00Z', 48), 3)

    expect(ticks[0]).toBe(Date.parse('2026-07-01T02:00:00Z')) // 03:00 UK time
  })
})

describe('buildDayTicks', () => {
  it('puts one tick at UK midnight of each day when there are few days', () => {
    const ticks = buildDayTicks(halfHourTimestamps('2026-01-02T00:00:00Z', 48 * 3))

    expect(ticks).toEqual([
      Date.parse('2026-01-02T00:00:00Z'),
      Date.parse('2026-01-03T00:00:00Z'),
      Date.parse('2026-01-04T00:00:00Z'),
    ])
  })

  it('thins the ticks to at most eight across a month', () => {
    const ticks = buildDayTicks(halfHourTimestamps('2026-01-02T00:00:00Z', 48 * 31))

    expect(ticks).toHaveLength(8)
    expect((ticks[1] ?? 0) - (ticks[0] ?? 0)).toBe(4 * 24 * 60 * 60 * 1000)
  })
})

describe('buildMwAxis', () => {
  it('rounds the top up to a round number with about four steps', () => {
    expect(buildMwAxis(15834)).toEqual({ max: 16000, ticks: [0, 4000, 8000, 12000, 16000] })
  })

  it('uses bigger steps for a bigger value', () => {
    expect(buildMwAxis(21353)).toEqual({
      max: 25000,
      ticks: [0, 5000, 10000, 15000, 20000, 25000],
    })
  })

  it('uses small steps for a small value', () => {
    expect(buildMwAxis(900)).toEqual({ max: 1000, ticks: [0, 500, 1000] })
  })

  it('still gives an axis when the value is zero', () => {
    expect(buildMwAxis(0)).toEqual({ max: 500, ticks: [0, 500] })
  })

  it('falls back to the biggest step for a very large value', () => {
    expect(buildMwAxis(120000).ticks[1]).toBe(10000)
  })
})

describe('buildSeriesChartData', () => {
  it('keeps the forecast and actual of each half-hour', () => {
    const rows = buildSeriesChartData(accuracyDataFixture.series.points)

    expect(rows[0]).toEqual({
      timestamp: Date.parse('2026-01-02T00:00:00Z'),
      forecastMw: 12000,
      actualMw: 9500,
    })
    expect(rows).toHaveLength(3)
  })
})

describe('buildHistogramRows', () => {
  it('labels each bin and marks negative-error bins as over-forecast', () => {
    const rows = buildHistogramRows(accuracyDataFixture.distribution.bins)

    expect(rows).toEqual([
      {
        label: '−500 MW to 0 MW',
        binStartMw: -500,
        binEndMw: 0,
        count: 40,
        direction: 'over-forecast',
      },
      {
        label: '0 MW to 500 MW',
        binStartMw: 0,
        binEndMw: 500,
        count: 10,
        direction: 'under-forecast',
      },
    ])
  })
})

describe('breakdown rows', () => {
  it('builds one row per hour of day', () => {
    expect(buildHourRows(accuracyDataFixture.hourly.hours)).toEqual([
      { hour: 0, label: '00:00', maeMw: 2030, biasMw: -1953 },
      { hour: 1, label: '01:00', maeMw: 2178, biasMw: -2133 },
    ])
  })

  it('builds one row per lead-time bin', () => {
    expect(buildHorizonRows(accuracyDataFixture.horizon.horizons)).toEqual([
      { label: '0–6 h', maeMw: 1665 },
      { label: '6–12 h', maeMw: 1739 },
    ])
  })

  it('builds one row per delivery day', () => {
    expect(buildDayRows(accuracyDataFixture.daily.days)).toEqual([
      { day: '2026-01-02', label: '2 Jan', maeMw: 1500 },
      { day: '2026-01-28', label: '28 Jan', maeMw: 5375 },
    ])
  })
})
