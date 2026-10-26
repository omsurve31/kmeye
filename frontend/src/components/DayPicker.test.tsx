import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DayPicker } from './DayPicker'

describe('DayPicker', () => {
  it('shows the selected day with its weekday', () => {
    render(<DayPicker day="2026-01-15" onChange={vi.fn()} />)

    expect(screen.getByLabelText('Delivery day')).toHaveValue('2026-01-15')
    expect(screen.getByText('Thu 15 Jan 2026')).toBeInTheDocument()
  })

  it('limits the date input to the delivery window', () => {
    render(<DayPicker day="2026-01-15" onChange={vi.fn()} />)

    const input = screen.getByLabelText('Delivery day')
    expect(input).toHaveAttribute('min', '2026-01-02')
    expect(input).toHaveAttribute('max', '2026-02-01')
  })

  it('moves to the next and previous day with the buttons', () => {
    const onChange = vi.fn()
    render(<DayPicker day="2026-01-15" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Next day' }))
    fireEvent.click(screen.getByRole('button', { name: 'Previous day' }))

    expect(onChange).toHaveBeenNthCalledWith(1, '2026-01-16')
    expect(onChange).toHaveBeenNthCalledWith(2, '2026-01-14')
  })

  it('disables the previous button on the first delivery day', () => {
    render(<DayPicker day="2026-01-02" onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Previous day' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Next day' })).toBeEnabled()
  })

  it('disables the next button on the last delivery day', () => {
    render(<DayPicker day="2026-02-01" onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Next day' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Previous day' })).toBeEnabled()
  })

  it('reports a valid day typed or picked in the input', () => {
    const onChange = vi.fn()
    render(<DayPicker day="2026-01-15" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('Delivery day'), { target: { value: '2026-01-20' } })

    expect(onChange).toHaveBeenCalledWith('2026-01-20')
  })

  it.each(['2026-03-01', '2025-12-31', ''])(
    'ignores %s because it is not a delivery day',
    (value) => {
      const onChange = vi.fn()
      render(<DayPicker day="2026-01-15" onChange={onChange} />)

      fireEvent.change(screen.getByLabelText('Delivery day'), { target: { value } })

      expect(onChange).not.toHaveBeenCalled()
    },
  )
})
