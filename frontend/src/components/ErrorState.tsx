import type { ApiError, ApiErrorKind } from '../api/client'

type ErrorStateProps = {
  error: ApiError
  onRetry: () => void
}

const TITLES: Record<ApiErrorKind, string> = {
  validation: 'That selection is not valid',
  'not-found': 'No data for this selection',
  unavailable: 'The data could not be loaded',
  network: 'The data could not be loaded',
  unexpected: 'The data could not be loaded',
}

// Trying again can only help when the problem might pass; a bad or empty selection needs a change.
const RETRYABLE_KINDS: ApiErrorKind[] = ['network', 'unavailable', 'unexpected']

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  return (
    <div className="state state--error" role="alert">
      <h3 className="state__title">{TITLES[error.kind]}</h3>
      <p className="state__message">{error.message}</p>
      {RETRYABLE_KINDS.includes(error.kind) && (
        <button type="button" className="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  )
}
