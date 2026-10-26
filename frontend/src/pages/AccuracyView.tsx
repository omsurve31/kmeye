import { BuyingSummaryPanel } from '../components/BuyingSummaryPanel'
import { ChartCard } from '../components/ChartCard'
import { CutoffControl } from '../components/CutoffControl'
import { DateRangeControl, type DayRange } from '../components/DateRangeControl'
import { ErrorByDayChart } from '../components/ErrorByDayChart'
import { ErrorByHorizonChart } from '../components/ErrorByHorizonChart'
import { ErrorByHourChart } from '../components/ErrorByHourChart'
import { ErrorHistogramChart } from '../components/ErrorHistogramChart'
import { ErrorState } from '../components/ErrorState'
import { ForecastActualChart } from '../components/ForecastActualChart'
import { LoadingState } from '../components/LoadingState'
import { StatTile } from '../components/StatTile'
import { ERROR_SIGN_NOTE } from '../constants'
import { useAccuracyData, type AccuracyData } from '../hooks/useAccuracyData'
import { formatMw, formatPercent, formatShortDate, formatSignedMw } from '../utils/format'

type AccuracyViewProps = {
  from: string
  to: string
  onRangeChange: (range: DayRange) => void
  cutoff: string
  onCutoffChange: (cutoff: string) => void
}

type AccuracyContentProps = {
  data: AccuracyData
  from: string
  to: string
  cutoff: string
}

function AccuracyContent({ data, from, to, cutoff }: AccuracyContentProps) {
  const summary = data.summary.summary
  // A negative 10th percentile error is the shortfall that happened in at least 10% of half-hours.
  const tailRiskMw = Math.max(0, -summary.errorP10Mw)

  return (
    <>
      <dl className="stat-strip stat-strip--five">
        <StatTile
          label="Mean absolute error (MAE)"
          value={formatMw(summary.maeMw)}
          caption="Typical size of a miss"
        />
        <StatTile
          label="Root mean square error (RMSE)"
          value={formatMw(summary.rmseMw)}
          caption="Counts big misses more"
        />
        <StatTile
          label="Bias (mean error)"
          value={formatSignedMw(summary.biasMw)}
          caption="Negative: forecast too high"
        />
        <StatTile
          label="Normalised error"
          value={formatPercent(summary.normalisedMaePercent)}
          caption="MAE as a share of average output"
        />
        <StatTile
          label="Over-forecast tail risk"
          value={formatMw(tailRiskMw)}
          caption="Forecast too high by more than this in 10% of half-hours"
        />
      </dl>
      <BuyingSummaryPanel
        summary={summary}
        context={{ firstDay: from, lastDay: to, cutoffTimeUk: cutoff }}
      />
      <p className="note">{ERROR_SIGN_NOTE}</p>
      <div className="chart-grid">
        <div className="chart-grid__wide">
          <ChartCard
            title="Forecast vs actual"
            description="Every half-hour in the selected days. The gap between the lines is the error."
          >
            <ForecastActualChart points={data.series.points} />
          </ChartCard>
        </div>
        <ChartCard
          title="Error distribution"
          description="How often the forecast missed by each amount."
        >
          <ErrorHistogramChart bins={data.distribution.bins} summary={data.distribution.summary} />
        </ChartCard>
        <ChartCard
          title="Error by hour of day"
          description="Whether some times of day are harder to forecast."
        >
          <ErrorByHourChart hours={data.hourly.hours} />
        </ChartCard>
        <ChartCard
          title="Error by forecast lead time"
          description="Forecasts published closer to the target hour are usually better, which is why the latest one before the cutoff is used."
        >
          <ErrorByHorizonChart horizons={data.horizon.horizons} />
        </ChartCard>
        <ChartCard title="Error by delivery day" description="Which days were hardest to forecast.">
          <ErrorByDayChart days={data.daily.days} />
        </ChartCard>
      </div>
    </>
  )
}

export function AccuracyView({
  from,
  to,
  onRangeChange,
  cutoff,
  onCutoffChange,
}: AccuracyViewProps) {
  const { state, retry } = useAccuracyData(from, to, cutoff)

  return (
    <div className="view">
      <header className="view__header">
        <h2 className="view__title">How much can we trust it?</h2>
        <p className="view__lede">
          Backward-looking accuracy of the forecast available at {cutoff} UK time on the day before
          delivery, for {formatShortDate(from)} to {formatShortDate(to)}.
        </p>
      </header>
      <div className="controls">
        <DateRangeControl from={from} to={to} onChange={onRangeChange} />
        <CutoffControl cutoff={cutoff} onChange={onCutoffChange} />
      </div>
      {state.status === 'loading' && <LoadingState label="the accuracy figures" />}
      {state.status === 'error' && <ErrorState error={state.error} onRetry={retry} />}
      {state.status === 'success' && (
        <AccuracyContent data={state.data} from={from} to={to} cutoff={cutoff} />
      )}
    </div>
  )
}
