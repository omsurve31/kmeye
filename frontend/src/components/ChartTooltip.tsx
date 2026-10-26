import type { ReactNode } from 'react'
import type { TooltipContentProps } from 'recharts'

export type ChartSwatch = 'forecast' | 'actual' | 'band' | 'over' | 'under' | 'magnitude'

export type TooltipRow = {
  label: string
  value: string
  swatch?: ChartSwatch
}

export type TooltipDescription = {
  title: string
  rows: TooltipRow[]
}

export function ChartTooltip({ title, rows }: TooltipDescription) {
  return (
    <div className="chart-tooltip">
      <p className="chart-tooltip__title">{title}</p>
      <dl className="chart-tooltip__rows">
        {rows.map((row) => (
          <div key={row.label} className="chart-tooltip__row">
            {row.swatch && <span className={`swatch swatch--${row.swatch}`} aria-hidden="true" />}
            <dt>{row.label}</dt>
            <dd>{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

// Builds the function Recharts calls to draw a tooltip: it finds the hovered data row and lets
// the chart describe it.
export function tooltipContent<Row>(describe: (row: Row) => TooltipDescription) {
  return function renderTooltip({ active, payload }: TooltipContentProps): ReactNode {
    const row = payload?.[0]?.payload as Row | undefined
    if (!active || !row) {
      return null
    }
    return <ChartTooltip {...describe(row)} />
  }
}
