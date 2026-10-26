import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import { ERROR_SIGN_NOTE } from '../constants'
import type { LoadState } from '../hooks/useApiData'
import { useAccuracyData, type AccuracyData } from '../hooks/useAccuracyData'
import { accuracyDataFixture } from '../test/fixtures'
import { AccuracyView } from './AccuracyView'

vi.mock('../hooks/useAccuracyData', () => ({ useAccuracyData: vi.fn() }))

const retry = vi.fn()

function showState(state: LoadState<AccuracyData>) {
  vi.mocked(useAccuracyData).mockReturnValue({ state, retry })
}

function renderView() {
  const props = {
    from: '2026-01-02',
    to: '2026-02-01',
    onRangeChange: vi.fn(),
    cutoff: '09:00',
    onCutoffChange: vi.fn(),
  }
  render(<AccuracyView {...props} />)
  return props
}

describe('AccuracyView', () => {
  beforeEach(() => {
    retry.mockReset()
    showState({ status: 'success', data: accuracyDataFixture })
  })

  it('asks the range and the cutoff for the data', () => {
    renderView()

    expect(useAccuracyData).toHaveBeenCalledWith('2026-01-02', '2026-02-01', '09:00')
  })

  it('shows a loading state while the accuracy loads', () => {
    showState({ status: 'loading' })
    renderView()

    expect(screen.getByRole('status')).toHaveTextContent('Loading the accuracy figures…')
  })

  it('shows the error and lets the user try again', () => {
    showState({
      status: 'error',
      error: new ApiError('unavailable', 'Temporarily unavailable.', 503),
    })
    renderView()

    expect(screen.getByRole('alert')).toHaveTextContent('Temporarily unavailable.')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(retry).toHaveBeenCalledTimes(1)
  })

  it('keeps the controls on screen when there is no data for the selection', () => {
    showState({
      status: 'error',
      error: new ApiError('not-found', 'No data for the selected days.'),
    })
    renderView()

    expect(screen.getByLabelText('From')).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Decision cutoff (UK time)' })).toBeInTheDocument()
  })

  it('asks the question the buyer has', () => {
    renderView()

    expect(screen.getByRole('heading', { name: 'How much can we trust it?' })).toBeInTheDocument()
  })

  it('shows the five headline numbers with their units', () => {
    renderView()

    expect(screen.getByText('Mean absolute error (MAE)')).toBeInTheDocument()
    expect(screen.getByText('2,042 MW')).toBeInTheDocument()
    expect(screen.getByText('Root mean square error (RMSE)')).toBeInTheDocument()
    expect(screen.getByText('2,509 MW')).toBeInTheDocument()
    expect(screen.getByText('Bias (mean error)')).toBeInTheDocument()
    expect(screen.getByText('−1,748 MW')).toBeInTheDocument()
    expect(screen.getByText('Normalised error')).toBeInTheDocument()
    expect(screen.getByText('18.1%')).toBeInTheDocument()
    expect(screen.getByText('Over-forecast tail risk')).toBeInTheDocument()
    expect(screen.getByText('4,140 MW')).toBeInTheDocument()
  })

  it('shows no shortfall when the forecast is rarely too high', () => {
    const summary = { ...accuracyDataFixture.summary.summary, errorP10Mw: 25 }
    showState({
      status: 'success',
      data: { ...accuracyDataFixture, summary: { ...accuracyDataFixture.summary, summary } },
    })
    renderView()

    expect(screen.getByText('0 MW')).toBeInTheDocument()
  })

  it('shows the plain-English summary for buying', () => {
    renderView()

    expect(screen.getByRole('heading', { name: 'What this means for buying' })).toBeInTheDocument()
    expect(screen.getByText(/finished within 3,900 MW of the forecast/)).toBeInTheDocument()
  })

  it('states the error sign convention', () => {
    renderView()

    expect(screen.getByText(ERROR_SIGN_NOTE)).toBeInTheDocument()
  })

  it('draws the five charts', () => {
    renderView()

    for (const name of [
      'Forecast vs actual',
      'Error distribution',
      'Error by hour of day',
      'Error by delivery day',
      'Error by forecast lead time',
    ]) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    }
  })

  it('reports a new range from the date controls', () => {
    const props = renderView()

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-10' } })

    expect(props.onRangeChange).toHaveBeenCalledWith({ from: '2026-01-10', to: '2026-02-01' })
  })

  it('reports a new cutoff from the cutoff control', () => {
    const props = renderView()

    fireEvent.change(screen.getByLabelText('Hour'), { target: { value: '12' } })

    expect(props.onCutoffChange).toHaveBeenCalledWith('12:00')
  })
})
