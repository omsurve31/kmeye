import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { metaFixture } from '../test/fixtures'
import { AboutData } from './AboutData'

describe('AboutData', () => {
  it('states the source, the scope and the error definition', () => {
    render(<AboutData meta={metaFixture} />)

    expect(screen.getByText('About this data')).toBeInTheDocument()
    expect(screen.getByText(/national wind generation/i)).toBeInTheDocument()
    expect(screen.getByText(/2 Jan 2026 to 1 Feb 2026/)).toBeInTheDocument()
    expect(screen.getByText(metaFixture.errorDefinition)).toBeInTheDocument()
  })

  it('explains how hourly forecasts are compared with half-hourly actuals', () => {
    render(<AboutData meta={metaFixture} />)

    expect(screen.getByText(/applied to both half-hours/i)).toBeInTheDocument()
  })

  it('shows how many rows were kept', () => {
    render(<AboutData meta={metaFixture} />)

    expect(screen.getByText(/14,383 of 20,440 forecast rows/)).toBeInTheDocument()
    expect(screen.getByText(/1,488 of 1,488 actual half-hours/)).toBeInTheDocument()
  })

  it('warns when actual half-hours are missing', () => {
    render(<AboutData meta={{ ...metaFixture, missingActualHalfHours: 3 }} />)

    expect(screen.getByText(/3 half-hours have no actual value/)).toBeInTheDocument()
  })
})
