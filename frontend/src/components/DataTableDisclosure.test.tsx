import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { DataTableDisclosure } from './DataTableDisclosure'

describe('DataTableDisclosure', () => {
  it('offers the chart data as a table behind a summary', () => {
    render(
      <DataTableDisclosure
        caption="Forecast by hour"
        columns={['Hour', 'Forecast']}
        rows={[
          ['00:00', '12,000 MW'],
          ['01:00', '11,000 MW'],
        ]}
      />,
    )

    expect(screen.getByText('View data as a table')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Forecast by hour' })
    expect(
      within(table)
        .getAllByRole('columnheader')
        .map((cell) => cell.textContent),
    ).toEqual(['Hour', 'Forecast'])
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByText('11,000 MW')).toBeInTheDocument()
  })
})
