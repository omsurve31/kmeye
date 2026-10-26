import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { errorSummaryFixture } from '../test/fixtures'
import { BuyingSummaryPanel } from './BuyingSummaryPanel'

const context = { firstDay: '2026-01-02', lastDay: '2026-02-01', cutoffTimeUk: '09:00' }

describe('BuyingSummaryPanel', () => {
  it('has a heading that says what the panel is for', () => {
    render(<BuyingSummaryPanel summary={errorSummaryFixture} context={context} />)

    expect(screen.getByRole('heading', { name: 'What this means for buying' })).toBeInTheDocument()
  })

  it('lists the plain-English statements', () => {
    render(<BuyingSummaryPanel summary={errorSummaryFixture} context={context} />)

    const items = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(items).toHaveLength(4)
    expect(items[0]).toHaveTextContent('within 3,900 MW of the forecast')
    expect(items[1]).toHaveTextContent('too high by more than 4,140 MW')
    expect(items[3]).toHaveTextContent('not a guarantee')
  })
})
