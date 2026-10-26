import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PublishNotice } from './PublishNotice'

describe('PublishNotice', () => {
  it('says which forecast the buyer saw, in UK time', () => {
    render(<PublishNotice publishTimesUtc={['2026-01-14T07:30:00Z']} />)

    expect(screen.getByText('Based on the forecast published at')).toBeInTheDocument()
    expect(screen.getByText('07:30 UK time on Wed 14 Jan 2026')).toBeInTheDocument()
  })

  it('names the first and last publish time when the day used several forecasts', () => {
    render(<PublishNotice publishTimesUtc={['2026-01-14T07:30:00Z', '2026-01-14T09:30:00Z']} />)

    expect(screen.getByText(/Based on forecasts published between/)).toBeInTheDocument()
    expect(screen.getByText('07:30 UK time on Wed 14 Jan 2026')).toBeInTheDocument()
    expect(screen.getByText('09:30 UK time on Wed 14 Jan 2026')).toBeInTheDocument()
  })
})
