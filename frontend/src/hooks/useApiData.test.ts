import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import { useApiData } from './useApiData'

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useApiData', () => {
  it('starts in the loading state', () => {
    const { result } = renderHook(() => useApiData(() => new Promise<number>(() => {})))

    expect(result.current.state).toEqual({ status: 'loading' })
  })

  it('moves to success with the loaded data', async () => {
    const load = vi.fn().mockResolvedValue(42)

    const { result } = renderHook(() => useApiData<number>(load))

    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 42 }))
  })

  it('keeps an ApiError as it is', async () => {
    const error = new ApiError('not-found', 'No data is available for this selection.', 404)
    const load = vi.fn().mockRejectedValue(error)

    const { result } = renderHook(() => useApiData<number>(load))

    await waitFor(() => expect(result.current.state).toEqual({ status: 'error', error }))
  })

  it('turns any other failure into an unexpected ApiError', async () => {
    const load = vi.fn().mockRejectedValue(new Error('internal details'))

    const { result } = renderHook(() => useApiData<number>(load))

    await waitFor(() => expect(result.current.state.status).toBe('error'))
    const state = result.current.state
    expect(state.status === 'error' && state.error.kind).toBe('unexpected')
    expect(state.status === 'error' && state.error.message).not.toContain('internal')
  })

  it('ignores an aborted request instead of showing an error', async () => {
    const load = vi.fn().mockRejectedValue(new DOMException('aborted', 'AbortError'))

    const { result } = renderHook(() => useApiData<number>(load))
    await act(async () => {
      await Promise.resolve()
    })

    expect(result.current.state).toEqual({ status: 'loading' })
  })

  it('shows loading again for a new request and ignores a late answer to the old one', async () => {
    const first = deferred<string>()
    const second = deferred<string>()
    const loadFirst = vi.fn().mockReturnValue(first.promise)
    const loadSecond = vi.fn().mockReturnValue(second.promise)
    const { result, rerender } = renderHook(({ load }) => useApiData<string>(load), {
      initialProps: { load: loadFirst },
    })

    rerender({ load: loadSecond })
    await act(async () => {
      first.resolve('old')
    })
    expect(result.current.state).toEqual({ status: 'loading' })

    await act(async () => {
      second.resolve('new')
    })
    await waitFor(() => expect(result.current.state).toEqual({ status: 'success', data: 'new' }))
  })

  it('loads again when retry is called', async () => {
    const load = vi
      .fn()
      .mockRejectedValueOnce(new ApiError('network', 'Could not reach the server.'))
      .mockResolvedValueOnce('recovered')
    const { result } = renderHook(() => useApiData<string>(load))
    await waitFor(() => expect(result.current.state.status).toBe('error'))

    act(() => {
      result.current.retry()
    })

    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'success', data: 'recovered' }),
    )
    expect(load).toHaveBeenCalledTimes(2)
  })

  it('aborts the request when the component goes away', () => {
    let seenSignal: AbortSignal | undefined
    const load = vi.fn((signal: AbortSignal) => {
      seenSignal = signal
      return new Promise<number>(() => {})
    })
    const { unmount } = renderHook(() => useApiData<number>(load))

    unmount()

    expect(seenSignal?.aborted).toBe(true)
  })
})
