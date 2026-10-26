import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ApiError,
  getAccuracySeries,
  getAccuracySummary,
  getDailyAccuracy,
  getDistribution,
  getHorizonAccuracy,
  getHourlyAccuracy,
} from '../api/client'
import { accuracyDataFixture } from '../test/fixtures'
import { useAccuracyData } from './useAccuracyData'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  getAccuracySummary: vi.fn(),
  getAccuracySeries: vi.fn(),
  getHourlyAccuracy: vi.fn(),
  getDailyAccuracy: vi.fn(),
  getDistribution: vi.fn(),
  getHorizonAccuracy: vi.fn(),
}))

const query = { from: '2026-01-02', to: '2026-01-10', cutoff: '09:00' }

beforeEach(() => {
  vi.mocked(getAccuracySummary).mockReset().mockResolvedValue(accuracyDataFixture.summary)
  vi.mocked(getAccuracySeries).mockReset().mockResolvedValue(accuracyDataFixture.series)
  vi.mocked(getHourlyAccuracy).mockReset().mockResolvedValue(accuracyDataFixture.hourly)
  vi.mocked(getDailyAccuracy).mockReset().mockResolvedValue(accuracyDataFixture.daily)
  vi.mocked(getDistribution).mockReset().mockResolvedValue(accuracyDataFixture.distribution)
  vi.mocked(getHorizonAccuracy).mockReset().mockResolvedValue(accuracyDataFixture.horizon)
})

describe('useAccuracyData', () => {
  it('loads every accuracy dataset in one go', async () => {
    const { result } = renderHook(() => useAccuracyData(query.from, query.to, query.cutoff))

    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'success', data: accuracyDataFixture }),
    )
  })

  it('sends the range and cutoff to the cutoff-based endpoints', async () => {
    renderHook(() => useAccuracyData(query.from, query.to, query.cutoff))

    await waitFor(() => expect(getAccuracySummary).toHaveBeenCalled())
    for (const endpoint of [
      getAccuracySummary,
      getAccuracySeries,
      getHourlyAccuracy,
      getDailyAccuracy,
      getDistribution,
    ]) {
      expect(endpoint).toHaveBeenCalledWith(query, expect.any(AbortSignal))
    }
  })

  it('sends only the range to the lead-time endpoint', async () => {
    renderHook(() => useAccuracyData(query.from, query.to, query.cutoff))

    await waitFor(() => expect(getHorizonAccuracy).toHaveBeenCalled())
    expect(getHorizonAccuracy).toHaveBeenCalledWith(
      { from: query.from, to: query.to },
      expect.any(AbortSignal),
    )
  })

  it('fails as a whole when one dataset fails', async () => {
    const error = new ApiError('not-found', 'No data is available for this selection.', 404)
    vi.mocked(getHourlyAccuracy).mockRejectedValue(error)

    const { result } = renderHook(() => useAccuracyData(query.from, query.to, query.cutoff))

    await waitFor(() => expect(result.current.state).toEqual({ status: 'error', error }))
  })
})
