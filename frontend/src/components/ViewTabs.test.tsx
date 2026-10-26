import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { panelId, tabId, ViewTabs } from './ViewTabs'

describe('ViewTabs', () => {
  it('marks the current view as selected', () => {
    render(<ViewTabs view="decision" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: "Tomorrow's forecast" })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByRole('tab', { name: 'Forecast accuracy' })).toHaveAttribute(
      'aria-selected',
      'false',
    )
  })

  it('links each tab to its panel', () => {
    render(<ViewTabs view="decision" onChange={vi.fn()} />)

    const tab = screen.getByRole('tab', { name: 'Forecast accuracy' })
    expect(tab).toHaveAttribute('id', tabId('accuracy'))
    expect(tab).toHaveAttribute('aria-controls', panelId('accuracy'))
  })

  it('switches view when a tab is clicked', () => {
    const onChange = vi.fn()
    render(<ViewTabs view="decision" onChange={onChange} />)

    fireEvent.click(screen.getByRole('tab', { name: 'Forecast accuracy' }))

    expect(onChange).toHaveBeenCalledWith('accuracy')
  })

  it('moves to the next tab with the right arrow key and wraps around', () => {
    const onChange = vi.fn()
    const { rerender } = render(<ViewTabs view="decision" onChange={onChange} />)

    fireEvent.keyDown(screen.getByRole('tab', { name: "Tomorrow's forecast" }), {
      key: 'ArrowRight',
    })
    rerender(<ViewTabs view="accuracy" onChange={onChange} />)
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Forecast accuracy' }), { key: 'ArrowRight' })

    expect(onChange).toHaveBeenNthCalledWith(1, 'accuracy')
    expect(onChange).toHaveBeenNthCalledWith(2, 'decision')
  })

  it('moves to the previous tab with the left arrow key', () => {
    const onChange = vi.fn()
    render(<ViewTabs view="accuracy" onChange={onChange} />)

    fireEvent.keyDown(screen.getByRole('tab', { name: 'Forecast accuracy' }), { key: 'ArrowLeft' })

    expect(onChange).toHaveBeenCalledWith('decision')
  })

  it('lets only the selected tab be reached with the tab key', () => {
    render(<ViewTabs view="decision" onChange={vi.fn()} />)

    expect(screen.getByRole('tab', { name: "Tomorrow's forecast" })).toHaveAttribute(
      'tabindex',
      '0',
    )
    expect(screen.getByRole('tab', { name: 'Forecast accuracy' })).toHaveAttribute('tabindex', '-1')
  })
})
