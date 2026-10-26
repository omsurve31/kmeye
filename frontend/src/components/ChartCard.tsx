import { useId, type ReactNode } from 'react'

type ChartCardProps = {
  title: string
  description?: ReactNode
  children: ReactNode
}

export function ChartCard({ title, description, children }: ChartCardProps) {
  const headingId = useId()
  return (
    <section className="chart-card" aria-labelledby={headingId}>
      <h3 id={headingId} className="chart-card__title">
        {title}
      </h3>
      {description && <p className="chart-card__description">{description}</p>}
      {children}
    </section>
  )
}
