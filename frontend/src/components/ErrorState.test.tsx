import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ApiError, type ApiErrorKind } from '../api/client'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('shows the error message in an alert', () => {
    render(
      <ErrorState
        error={new ApiError('network', 'Could not reach the server.')}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('Could not reach the server.')
  })

  it.each<ApiErrorKind>(['network', 'unavailable', 'unexpected'])(
    'offers a retry for a %s error and calls onRetry when it is used',
    (kind) => {
      const onRetry = vi.fn()
      render(<ErrorState error={new ApiError(kind, 'Something failed.')} onRetry={onRetry} />)

      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))

      expect(onRetry).toHaveBeenCalledTimes(1)
    },
  )

  it('explains a not-found error without a retry button', () => {
    render(
      <ErrorState
        error={new ApiError('not-found', 'No data is available.', 404)}
        onRetry={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: 'No data for this selection' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })

  it('explains a validation error without a retry button', () => {
    render(
      <ErrorState error={new ApiError('validation', 'day: not valid', 422)} onRetry={vi.fn()} />,
    )

    expect(screen.getByRole('heading', { name: 'That selection is not valid' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })
})
