import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { decisionFixture } from '../test/fixtures'
import { ForecastBandChart } from './ForecastBandChart'

const props = { points: decisionFixture.points, deliveryDayLabel: 'Thu 15 Jan 2026' }

describe('ForecastBandChart', () => {
  it('describes the chart for assistive technology, with the range of the forecast', () => {
    render(<ForecastBandChart {...props} shouldShowActual />)

    expect(
      screen.getByRole('img', {
        name: 'Chart of forecast wind generation in MW for Thu 15 Jan 2026, from 11,000 MW to 12,000 MW.',
      }),
    ).toBeInTheDocument()
  })

  it('has a legend for the forecast, the typical range and the actual outturn', () => {
    render(<ForecastBandChart {...props} shouldShowActual />)

    const legend = within(screen.getByRole('list'))
    expect(legend.getByText('Forecast')).toBeInTheDocument()
    expect(legend.getByText('Typical range (P10 to P90)')).toBeInTheDocument()
    expect(legend.getByText('Actual outturn')).toBeInTheDocument()
  })

  it('draws a line for the forecast and one for the actual outturn', () => {
    const { container } = render(<ForecastBandChart {...props} shouldShowActual />)

    expect(container.querySelectorAll('.recharts-line')).toHaveLength(2)
  })

  it('leaves the actual outturn out of the legend and the chart when it is hidden', () => {
    const { container } = render(<ForecastBandChart {...props} shouldShowActual={false} />)

    expect(within(screen.getByRole('list')).queryByText('Actual outturn')).not.toBeInTheDocument()
    expect(container.querySelectorAll('.recharts-line')).toHaveLength(1)
  })

  it('offers the numbers as a table with one row per half-hour', () => {
    render(<ForecastBandChart {...props} shouldShowActual />)

    const table = screen.getByRole('table', {
      name: 'Forecast wind generation for Thu 15 Jan 2026',
    })
    expect(table.querySelectorAll('tbody tr')).toHaveLength(4)
    expect(table).toHaveTextContent('12,000 MW')
    expect(table).toHaveTextContent('not available')
  })
})
