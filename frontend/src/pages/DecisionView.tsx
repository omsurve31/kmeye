import { useState } from 'react'

import { ChartCard } from '../components/ChartCard'
import { CutoffControl } from '../components/CutoffControl'
import { DayPicker } from '../components/DayPicker'
import { ErrorState } from '../components/ErrorState'
import { ForecastBandChart } from '../components/ForecastBandChart'
import { LoadingState } from '../components/LoadingState'
import { PublishNotice } from '../components/PublishNotice'
import { StatTile } from '../components/StatTile'
import { useDecisionData } from '../hooks/useDecisionData'
import type { Decision } from '../types/api'
import { shiftDay } from '../utils/days'
import { formatDayLabel, formatMw, formatMwh } from '../utils/format'

type DecisionViewProps = {
  day: string
  onDayChange: (day: string) => void
  cutoff: string
  onCutoffChange: (cutoff: string) => void
}

type DecisionContentProps = {
  decision: Decision
}

function DecisionContent({ decision }: DecisionContentProps) {
  const [shouldShowActual, setShouldShowActual] = useState(true)
  const dayLabel = formatDayLabel(decision.deliveryDay)
  const missing = decision.missingHalfHours

  return (
    <>
      <PublishNotice publishTimesUtc={decision.forecastPublishTimesUtc} />
      <dl className="stat-strip stat-strip--four">
        <StatTile
          label="Expected total"
          value={formatMwh(decision.expectedTotalMwh)}
          caption="Forecast energy over the day"
        />
        <StatTile
          label="Average"
          value={formatMw(decision.averageMw)}
          caption="Mean forecast over the day"
        />
        <StatTile label="Peak" value={formatMw(decision.peakMw)} caption="Highest half-hour" />
        <StatTile label="Minimum" value={formatMw(decision.minimumMw)} caption="Lowest half-hour" />
      </dl>
      {missing > 0 && (
        <p className="note note--warning">
          {missing} {missing === 1 ? 'half-hour has' : 'half-hours have'} no forecast at this
          cutoff, so the totals cover only part of the day.
        </p>
      )}
      <ChartCard
        title="Forecast wind generation"
        description="What the buyer could see at the cutoff, half-hour by half-hour."
      >
        <label className="toggle">
          <input
            type="checkbox"
            checked={shouldShowActual}
            onChange={(event) => setShouldShowActual(event.target.checked)}
          />
          Show actual outturn
        </label>
        <ForecastBandChart
          points={decision.points}
          deliveryDayLabel={dayLabel}
          shouldShowActual={shouldShowActual}
        />
        <p className="note">
          The shaded band is where output usually landed: the forecast plus the 10th to 90th
          percentile of January forecast errors for the same hour of day. It is backward-looking
          evidence from January 2026, not a guarantee.
        </p>
      </ChartCard>
    </>
  )
}

export function DecisionView({ day, onDayChange, cutoff, onCutoffChange }: DecisionViewProps) {
  const { state, retry } = useDecisionData(day, cutoff)

  return (
    <div className="view">
      <header className="view__header">
        <h2 className="view__title">What will wind give us tomorrow?</h2>
        <p className="view__lede">
          Delivery on {formatDayLabel(day)}, decided by {cutoff} UK time on{' '}
          {formatDayLabel(shiftDay(day, -1))}.
        </p>
      </header>
      <div className="controls">
        <DayPicker day={day} onChange={onDayChange} />
        <CutoffControl cutoff={cutoff} onChange={onCutoffChange} />
      </div>
      {state.status === 'loading' && <LoadingState label="the forecast" />}
      {state.status === 'error' && <ErrorState error={state.error} onRetry={retry} />}
      {state.status === 'success' && <DecisionContent decision={state.data} />}
    </div>
  )
}
