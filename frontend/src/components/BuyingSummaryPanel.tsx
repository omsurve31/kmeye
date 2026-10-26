import { useId } from 'react'

import type { ErrorSummary } from '../types/api'
import { buildBuyingSummary, type SummaryContext } from '../utils/summaryText'

type BuyingSummaryPanelProps = {
  summary: ErrorSummary
  context: SummaryContext
}

export function BuyingSummaryPanel({ summary, context }: BuyingSummaryPanelProps) {
  const headingId = useId()
  return (
    <section className="panel" aria-labelledby={headingId}>
      <h3 id={headingId} className="panel__title">
        What this means for buying
      </h3>
      <ul className="panel__list">
        {buildBuyingSummary(summary, context).map((sentence) => (
          <li key={sentence}>{sentence}</li>
        ))}
      </ul>
    </section>
  )
}
