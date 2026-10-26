import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { CutoffControl } from './CutoffControl'

describe('CutoffControl', () => {
  it('is a labelled group with a 24-hour hour and minute', () => {
    render(<CutoffControl cutoff="09:30" onChange={vi.fn()} />)

    expect(screen.getByRole('group', { name: 'Decision cutoff (UK time)' })).toBeInTheDocument()
    expect(screen.getByLabelText('Hour')).toHaveValue('09')
    expect(screen.getByLabelText('Minute')).toHaveValue('30')
  })

  it('offers all 24 hours and quarter-hour minutes', () => {
    render(<CutoffControl cutoff="09:00" onChange={vi.fn()} />)

    const hours = within(screen.getByLabelText('Hour')).getAllByRole('option')
    const minutes = within(screen.getByLabelText('Minute')).getAllByRole('option')
    expect(hours.map((option) => option.textContent)).toHaveLength(24)
    expect(hours[0]).toHaveTextContent('00')
    expect(hours[23]).toHaveTextContent('23')
    expect(minutes.map((option) => option.textContent)).toEqual(['00', '15', '30', '45'])
  })

  it('reports a new hour and keeps the minute', () => {
    const onChange = vi.fn()
    render(<CutoffControl cutoff="09:30" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Hour'), { target: { value: '10' } })

    expect(onChange).toHaveBeenCalledWith('10:30')
  })

  it('reports a new minute and keeps the hour', () => {
    const onChange = vi.fn()
    render(<CutoffControl cutoff="09:00" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Minute'), { target: { value: '45' } })

    expect(onChange).toHaveBeenCalledWith('09:45')
  })

  it('still shows a minute that is not a quarter hour', () => {
    render(<CutoffControl cutoff="09:10" onChange={vi.fn()} />)

    expect(screen.getByLabelText('Minute')).toHaveValue('10')
  })

  it('explains the rule and when new forecasts are published', () => {
    render(<CutoffControl cutoff="09:00" onChange={vi.fn()} />)

    const hint = screen.getByText(/latest forecast published before this time/i)
    expect(hint).toHaveTextContent('day before delivery')
    expect(hint).toHaveTextContent('07:30')
    expect(hint).toHaveTextContent('09:30')
  })
})
