import { fireEvent, render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../api/client'
import { useDecisionData } from '../hooks/useDecisionData'
import type { LoadState } from '../hooks/useApiData'
import { decisionFixture } from '../test/fixtures'
import type { Decision } from '../types/api'
import { DecisionView } from './DecisionView'

vi.mock('../hooks/useDecisionData', () => ({ useDecisionData: vi.fn() }))

const retry = vi.fn()

function showState(state: LoadState<Decision>) {
  vi.mocked(useDecisionData).mockReturnValue({ state, retry })
}

function renderView() {
  const props = {
    day: '2026-01-15',
    onDayChange: vi.fn(),
    cutoff: '09:00',
    onCutoffChange: vi.fn(),
  }
  render(<DecisionView {...props} />)
  return props
}

describe('DecisionView', () => {
  beforeEach(() => {
    retry.mockReset()
    showState({ status: 'success', data: decisionFixture })
  })

  it('asks the day and the cutoff for the data', () => {
    renderView()

    expect(useDecisionData).toHaveBeenCalledWith('2026-01-15', '09:00')
  })

  it('shows a loading state while the forecast loads', () => {
    showState({ status: 'loading' })
    renderView()

    expect(screen.getByRole('status')).toHaveTextContent('Loading the forecast…')
  })

  it('shows the error and lets the user try again', () => {
    showState({ status: 'error', error: new ApiError('network', 'Could not reach the server.') })
    renderView()

    expect(screen.getByRole('alert')).toHaveTextContent('Could not reach the server.')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(retry).toHaveBeenCalledTimes(1)
  })

  it('keeps the controls on screen when there is no data for the selection', () => {
    showState({ status: 'error', error: new ApiError('not-found', 'No forecast was published.') })
    renderView()

    expect(screen.getByRole('heading', { name: 'No data for this selection' })).toBeInTheDocument()
    expect(screen.getByLabelText('Delivery day')).toBeInTheDocument()
  })

  it('asks the question the buyer has and names the delivery and decision days', () => {
    renderView()

    expect(
      screen.getByRole('heading', { name: 'What will wind give us tomorrow?' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/Delivery on Thu 15 Jan 2026/)).toHaveTextContent(
      'decided by 09:00 UK time on Wed 14 Jan 2026',
    )
  })

  it('shows which forecast the numbers are based on', () => {
    renderView()

    expect(screen.getByText('Based on the forecast published at')).toBeInTheDocument()
    expect(screen.getByText('07:30 UK time on Wed 14 Jan 2026')).toBeInTheDocument()
  })

  it('shows the headline numbers with their units', () => {
    renderView()

    expect(screen.getByText('Expected total')).toBeInTheDocument()
    expect(screen.getByText('23,000 MWh')).toBeInTheDocument()
    expect(screen.getByText('11,500 MW')).toBeInTheDocument()
    expect(screen.getByText('12,000 MW', { selector: 'dd' })).toBeInTheDocument()
    expect(screen.getByText('11,000 MW', { selector: 'dd' })).toBeInTheDocument()
  })

  it('draws the forecast chart and states that the band is backward-looking', () => {
    renderView()

    expect(
      screen.getByRole('img', { name: /Chart of forecast wind generation/ }),
    ).toBeInTheDocument()
    expect(screen.getByText(/not a guarantee/i)).toBeInTheDocument()
  })

  it('shows the actual outturn by default and hides it when switched off', () => {
    renderView()
    const legend = within(screen.getByRole('list'))
    expect(legend.getByText('Actual outturn')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('checkbox', { name: 'Show actual outturn' }))

    expect(legend.queryByText('Actual outturn')).not.toBeInTheDocument()
  })

  it('warns when some half-hours of the day have no forecast', () => {
    showState({ status: 'success', data: { ...decisionFixture, missingHalfHours: 4 } })
    renderView()

    expect(screen.getByText(/4 half-hours have no forecast/)).toBeInTheDocument()
  })

  it('reports a new day from the day picker', () => {
    const props = renderView()

    fireEvent.click(screen.getByRole('button', { name: 'Next day' }))

    expect(props.onDayChange).toHaveBeenCalledWith('2026-01-16')
  })

  it('reports a new cutoff from the cutoff control', () => {
    const props = renderView()

    fireEvent.change(screen.getByLabelText('Hour'), { target: { value: '10' } })

    expect(props.onCutoffChange).toHaveBeenCalledWith('10:00')
  })
})
