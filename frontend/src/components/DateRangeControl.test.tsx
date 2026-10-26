import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { DateRangeControl } from './DateRangeControl'

describe('DateRangeControl', () => {
  it('shows the selected range', () => {
    render(<DateRangeControl from="2026-01-05" to="2026-01-12" onChange={vi.fn()} />)

    expect(screen.getByLabelText('From')).toHaveValue('2026-01-05')
    expect(screen.getByLabelText('To')).toHaveValue('2026-01-12')
  })

  it('reports a new start day', () => {
    const onChange = vi.fn()
    render(<DateRangeControl from="2026-01-05" to="2026-01-12" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-08' } })

    expect(onChange).toHaveBeenCalledWith({ from: '2026-01-08', to: '2026-01-12' })
  })

  it('moves the end day along when the start day is set after it', () => {
    const onChange = vi.fn()
    render(<DateRangeControl from="2026-01-05" to="2026-01-12" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('From'), { target: { value: '2026-01-20' } })

    expect(onChange).toHaveBeenCalledWith({ from: '2026-01-20', to: '2026-01-20' })
  })

  it('moves the start day back when the end day is set before it', () => {
    const onChange = vi.fn()
    render(<DateRangeControl from="2026-01-10" to="2026-01-12" onChange={onChange} />)

    fireEvent.change(screen.getByLabelText('To'), { target: { value: '2026-01-05' } })

    expect(onChange).toHaveBeenCalledWith({ from: '2026-01-05', to: '2026-01-05' })
  })

  it.each(['2026-03-01', '2025-12-31', ''])(
    'ignores %s because it is not a delivery day',
    (value) => {
      const onChange = vi.fn()
      render(<DateRangeControl from="2026-01-05" to="2026-01-12" onChange={onChange} />)

      fireEvent.change(screen.getByLabelText('To'), { target: { value } })

      expect(onChange).not.toHaveBeenCalled()
    },
  )

  it('resets to the whole delivery window', () => {
    const onChange = vi.fn()
    render(<DateRangeControl from="2026-01-05" to="2026-01-12" onChange={onChange} />)

    fireEvent.click(screen.getByRole('button', { name: 'Whole window' }))

    expect(onChange).toHaveBeenCalledWith({ from: '2026-01-02', to: '2026-02-01' })
  })

  it('disables the reset when the whole window is already selected', () => {
    render(<DateRangeControl from="2026-01-02" to="2026-02-01" onChange={vi.fn()} />)

    expect(screen.getByRole('button', { name: 'Whole window' })).toBeDisabled()
  })
})
