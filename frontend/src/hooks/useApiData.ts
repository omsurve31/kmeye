import { useCallback, useEffect, useState } from 'react'

import { ApiError } from '../api/client'

export type LoadState<T> =
  { status: 'loading' } | { status: 'error'; error: ApiError } | { status: 'success'; data: T }

export type Loader<T> = (signal: AbortSignal) => Promise<T>

type Settled<T> = { load: Loader<T>; attempt: number; state: LoadState<T> }

const LOADING: LoadState<never> = { status: 'loading' }
const UNEXPECTED_MESSAGE = 'Something went wrong while loading the data.'

function toApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError('unexpected', UNEXPECTED_MESSAGE)
}

function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === 'AbortError'
}

// Runs `load` whenever it changes. The loader must keep the same identity between renders
// (wrap it in useCallback with its inputs). State is set only when a request finishes, and a
// finished request is shown only if it still matches the current loader and attempt, so a late
// answer to an old request can never replace the current one.
export function useApiData<T>(load: Loader<T>): { state: LoadState<T>; retry: () => void } {
  const [attempt, setAttempt] = useState(0)
  const [settled, setSettled] = useState<Settled<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal).then(
      (data) => setSettled({ load, attempt, state: { status: 'success', data } }),
      (error: unknown) => {
        if (!isAbort(error)) {
          setSettled({ load, attempt, state: { status: 'error', error: toApiError(error) } })
        }
      },
    )
    return () => controller.abort()
  }, [load, attempt])

  const retry = useCallback(() => setAttempt((count) => count + 1), [])
  const isCurrent = settled !== null && settled.load === load && settled.attempt === attempt
  return { state: isCurrent ? settled.state : LOADING, retry }
}
