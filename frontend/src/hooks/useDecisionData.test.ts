import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getDecision } from '../api/client'
import { decisionFixture } from '../test/fixtures'
import { useDecisionData } from './useDecisionData'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  getDecision: vi.fn(),
}))

describe('useDecisionData', () => {
  beforeEach(() => {
    vi.mocked(getDecision).mockReset()
    vi.mocked(getDecision).mockResolvedValue(decisionFixture)
  })

  it('requests the delivery day and cutoff and returns the decision', async () => {
    const { result } = renderHook(() => useDecisionData('2026-01-15', '09:00'))

    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'success', data: decisionFixture }),
    )
    expect(getDecision).toHaveBeenCalledWith(
      { day: '2026-01-15', cutoff: '09:00' },
      expect.any(AbortSignal),
    )
  })

  it('requests again when the day changes', async () => {
    const { result, rerender } = renderHook(({ day }) => useDecisionData(day, '09:00'), {
      initialProps: { day: '2026-01-15' },
    })
    await waitFor(() => expect(result.current.state.status).toBe('success'))

    rerender({ day: '2026-01-16' })

    await waitFor(() => expect(getDecision).toHaveBeenCalledTimes(2))
    expect(vi.mocked(getDecision).mock.calls[1]?.[0]).toEqual({
      day: '2026-01-16',
      cutoff: '09:00',
    })
  })

  it('requests again when the cutoff changes', async () => {
    const { rerender } = renderHook(({ cutoff }) => useDecisionData('2026-01-15', cutoff), {
      initialProps: { cutoff: '09:00' },
    })

    rerender({ cutoff: '10:30' })

    await waitFor(() => expect(getDecision).toHaveBeenCalledTimes(2))
    expect(vi.mocked(getDecision).mock.calls[1]?.[0]).toEqual({
      day: '2026-01-15',
      cutoff: '10:30',
    })
  })
})
