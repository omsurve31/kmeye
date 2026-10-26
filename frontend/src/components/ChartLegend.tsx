import type { ChartSwatch } from './ChartTooltip'

export type LegendItem = {
  label: string
  swatch: ChartSwatch
}

type ChartLegendProps = {
  items: LegendItem[]
}

// A legend sits above every chart so colour is never the only way to tell the series apart.
export function ChartLegend({ items }: ChartLegendProps) {
  return (
    <ul className="legend">
      {items.map((item) => (
        <li key={item.label} className="legend__item">
          <span className={`swatch swatch--${item.swatch}`} aria-hidden="true" />
          {item.label}
        </li>
      ))}
    </ul>
  )
}
