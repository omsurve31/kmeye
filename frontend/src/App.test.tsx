import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from './api/client'
import App from './App'
import { APP_SUBTITLE, APP_TITLE } from './constants'
import { useAccuracyData } from './hooks/useAccuracyData'
import { useDecisionData } from './hooks/useDecisionData'
import { useMeta } from './hooks/useMeta'
import { accuracyDataFixture, decisionFixture, metaFixture } from './test/fixtures'

vi.mock('./hooks/useMeta', () => ({ useMeta: vi.fn() }))
vi.mock('./hooks/useDecisionData', () => ({ useDecisionData: vi.fn() }))
vi.mock('./hooks/useAccuracyData', () => ({ useAccuracyData: vi.fn() }))

const retry = vi.fn()

beforeEach(() => {
  vi.mocked(useMeta).mockReturnValue({ state: { status: 'success', data: metaFixture }, retry })
  vi.mocked(useDecisionData)
    .mockReset()
    .mockReturnValue({ state: { status: 'success', data: decisionFixture }, retry })
  vi.mocked(useAccuracyData)
    .mockReset()
    .mockReturnValue({ state: { status: 'success', data: accuracyDataFixture }, retry })
})

describe('App', () => {
  it('renders the portal title as the main heading and the subtitle', () => {
    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: APP_TITLE })).toBeInTheDocument()
    expect(screen.getByText(APP_SUBTITLE)).toBeInTheDocument()
  })

  it('opens on the decision view for the default day and cutoff', () => {
    render(<App />)

    expect(
      screen.getByRole('heading', { name: 'What will wind give us tomorrow?' }),
    ).toBeInTheDocument()
    expect(useDecisionData).toHaveBeenLastCalledWith('2026-01-15', '09:00')
  })

  it('switches to the accuracy view for the whole window', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))

    expect(screen.getByRole('heading', { name: 'How much can we trust it?' })).toBeInTheDocument()
    expect(useAccuracyData).toHaveBeenLastCalledWith('2026-01-02', '2026-02-01', '09:00')
    expect(screen.getByRole('tabpanel')).toHaveAttribute('aria-labelledby', 'tab-accuracy')
  })

  it('uses the same cutoff in both views', () => {
    render(<App />)

    fireEvent.change(screen.getByLabelText('Hour'), { target: { value: '10' } })
    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))

    expect(useAccuracyData).toHaveBeenLastCalledWith('2026-01-02', '2026-02-01', '10:00')
  })

  it('remembers the chosen day when the user comes back to the decision view', () => {
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Next day' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))
    fireEvent.click(screen.getByRole('tab', { name: "Tomorrow's forecast" }))

    expect(useDecisionData).toHaveBeenLastCalledWith('2026-01-16', '09:00')
  })

  it('remembers the chosen range when the user comes back to the accuracy view', () => {
    render(<App />)
    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-10' } })
    fireEvent.click(screen.getByRole('tab', { name: "Tomorrow's forecast" }))
    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))

    expect(useAccuracyData).toHaveBeenLastCalledWith('2026-01-10', '2026-02-01', '09:00')
  })

  it('describes the data once it has loaded', () => {
    render(<App />)

    expect(screen.getByText('About this data')).toBeInTheDocument()
  })

  it('leaves out the data description while it loads or if it cannot be loaded', () => {
    vi.mocked(useMeta).mockReturnValue({ state: { status: 'loading' }, retry })
    const { unmount } = render(<App />)
    expect(screen.queryByText('About this data')).not.toBeInTheDocument()
    unmount()

    vi.mocked(useMeta).mockReturnValue({
      state: { status: 'error', error: new ApiError('network', 'Could not reach the server.') },
      retry,
    })
    render(<App />)

    expect(screen.queryByText('About this data')).not.toBeInTheDocument()
  })
})
