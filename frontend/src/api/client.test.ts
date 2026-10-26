import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ApiError,
  getAccuracySeries,
  getAccuracySummary,
  getDailyAccuracy,
  getDecision,
  getDistribution,
  getHorizonAccuracy,
  getHourlyAccuracy,
  getMeta,
} from './client'

const fetchMock = vi.fn()

function respondWith(status: number, body: unknown): void {
  fetchMock.mockResolvedValueOnce(
    new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }),
  )
}

function lastRequestUrl(): URL {
  const requested = fetchMock.mock.calls.at(-1)?.[0] as string
  return new URL(requested, 'http://localhost')
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  fetchMock.mockReset()
  vi.unstubAllGlobals()
})

describe('request building', () => {
  it('sends the delivery day and cutoff to /api/decision', async () => {
    respondWith(200, {})

    await getDecision({ day: '2026-01-15', cutoff: '09:00' })

    const url = lastRequestUrl()
    expect(url.pathname).toBe('/api/decision')
    expect(url.searchParams.get('day')).toBe('2026-01-15')
    expect(url.searchParams.get('cutoff')).toBe('09:00')
  })

  it.each([
    ['/api/accuracy/summary', getAccuracySummary],
    ['/api/accuracy/series', getAccuracySeries],
    ['/api/accuracy/by-hour', getHourlyAccuracy],
    ['/api/accuracy/by-day', getDailyAccuracy],
    ['/api/accuracy/distribution', getDistribution],
  ])('sends from, to and cutoff to %s', async (path, fetchData) => {
    respondWith(200, {})

    await fetchData({ from: '2026-01-02', to: '2026-01-10', cutoff: '10:30' })

    const url = lastRequestUrl()
    expect(url.pathname).toBe(path)
    expect(url.searchParams.get('from')).toBe('2026-01-02')
    expect(url.searchParams.get('to')).toBe('2026-01-10')
    expect(url.searchParams.get('cutoff')).toBe('10:30')
  })

  it('sends only from and to to /api/accuracy/by-horizon', async () => {
    respondWith(200, {})

    await getHorizonAccuracy({ from: '2026-01-02', to: '2026-01-10' })

    const url = lastRequestUrl()
    expect(url.pathname).toBe('/api/accuracy/by-horizon')
    expect([...url.searchParams.keys()]).toEqual(['from', 'to'])
  })

  it('sends no query string to /api/meta', async () => {
    respondWith(200, {})

    await getMeta()

    expect(lastRequestUrl().search).toBe('')
  })

  it('passes the abort signal to fetch', async () => {
    respondWith(200, {})
    const controller = new AbortController()

    await getMeta(controller.signal)

    expect(fetchMock.mock.calls[0]?.[1]).toMatchObject({ signal: controller.signal })
  })
})

describe('response conversion', () => {
  it('converts snake_case keys to camelCase at every depth', async () => {
    respondWith(200, {
      delivery_day: '2026-01-15',
      forecast_publish_times_utc: ['2026-01-14T07:30:00Z'],
      points: [
        {
          start_time_utc: '2026-01-15T00:00:00Z',
          forecast_mw: 1000,
          band_low_mw: 760,
          band_high_mw: null,
          actual_mw: 900,
        },
      ],
    })

    const decision = await getDecision({ day: '2026-01-15', cutoff: '09:00' })

    expect(decision).toEqual({
      deliveryDay: '2026-01-15',
      forecastPublishTimesUtc: ['2026-01-14T07:30:00Z'],
      points: [
        {
          startTimeUtc: '2026-01-15T00:00:00Z',
          forecastMw: 1000,
          bandLowMw: 760,
          bandHighMw: null,
          actualMw: 900,
        },
      ],
    })
  })

  it('converts percentile keys that contain digits', async () => {
    respondWith(200, { summary: { error_p5_mw: -1, error_p95_mw: 2, abs_error_p90_mw: 3 } })

    const result = await getAccuracySummary({
      from: '2026-01-02',
      to: '2026-02-01',
      cutoff: '09:00',
    })

    expect(result).toEqual({ summary: { errorP5Mw: -1, errorP95Mw: 2, absErrorP90Mw: 3 } })
  })
})

describe('errors', () => {
  it('turns a 422 into a validation error with the server message', async () => {
    respondWith(422, { detail: 'cutoff: String should have at most 5 characters' })

    await expect(getDecision({ day: '2026-01-15', cutoff: 'x' })).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'validation',
      status: 422,
      message: 'cutoff: String should have at most 5 characters',
    })
  })

  it('turns a 404 into a not-found error with the server message', async () => {
    respondWith(404, { detail: 'no forecast/actual data for the selected days' })

    await expect(getMeta()).rejects.toMatchObject({
      kind: 'not-found',
      status: 404,
      message: 'no forecast/actual data for the selected days',
    })
  })

  it('uses a default message when a 404 has no readable body', async () => {
    respondWith(404, 'not json')

    await expect(getMeta()).rejects.toMatchObject({
      kind: 'not-found',
      message: 'No data is available for this selection.',
    })
  })

  it('turns a 503 into an unavailable error with a friendly message', async () => {
    respondWith(503, { detail: 'The data snapshot is unavailable.' })

    await expect(getMeta()).rejects.toMatchObject({
      kind: 'unavailable',
      status: 503,
      message: 'The forecast data is temporarily unavailable. Please try again shortly.',
    })
  })

  it('turns any other failing status into an unexpected error', async () => {
    respondWith(500, { detail: 'boom with internal details' })

    const error = await getMeta().catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ kind: 'unexpected', status: 500 })
    expect((error as ApiError).message).not.toContain('internal')
  })

  it('turns a failed request into a network error', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Failed to fetch'))

    await expect(getMeta()).rejects.toMatchObject({
      kind: 'network',
      status: null,
      message: 'Could not reach the server. Check your connection and try again.',
    })
  })

  it('lets an abort through unchanged so callers can ignore it', async () => {
    fetchMock.mockRejectedValueOnce(new DOMException('aborted', 'AbortError'))

    await expect(getMeta()).rejects.toMatchObject({ name: 'AbortError' })
  })

  it('treats a 200 response that is not JSON as an unexpected error', async () => {
    respondWith(200, 'not json')

    await expect(getMeta()).rejects.toMatchObject({ kind: 'unexpected', status: 200 })
  })
})
