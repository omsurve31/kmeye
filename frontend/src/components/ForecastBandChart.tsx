import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX, TIME_TICK_EVERY_HOURS } from '../constants'
import type { DecisionPoint } from '../types/api'
import {
  buildDecisionChartData,
  buildMwAxis,
  buildTimeTicks,
  type DecisionChartRow,
} from '../utils/chartData'
import { formatMw, formatThousands, formatTimeUk } from '../utils/format'
import { ChartLegend, type LegendItem } from './ChartLegend'
import { tooltipContent, type TooltipRow } from './ChartTooltip'
import {
  AXIS_LINE,
  AXIS_TICK,
  CHART_MARGIN,
  X_AXIS_HEIGHT,
  Y_AXIS_WIDTH,
  xAxisLabel,
  yAxisLabel,
} from './chartStyle'
import { DataTableDisclosure } from './DataTableDisclosure'

type ForecastBandChartProps = {
  points: DecisionPoint[]
  deliveryDayLabel: string
  shouldShowActual: boolean
}

const NOT_AVAILABLE = 'not available'

function timestampToUkTime(timestamp: number): string {
  return formatTimeUk(new Date(timestamp).toISOString())
}

function describeRow(row: DecisionChartRow, shouldShowActual: boolean) {
  const rows: TooltipRow[] = [
    { label: 'Forecast', value: formatMw(row.forecastMw), swatch: 'forecast' },
  ]
  if (row.band) {
    rows.push({
      label: 'Typical range',
      value: `${formatMw(row.band[0])} to ${formatMw(row.band[1])}`,
      swatch: 'band',
    })
  }
  if (shouldShowActual) {
    const actual = row.actualMw === null ? NOT_AVAILABLE : formatMw(row.actualMw)
    rows.push({ label: 'Actual outturn', value: actual, swatch: 'actual' })
  }
  return { title: `${timestampToUkTime(row.timestamp)} UK time`, rows }
}

function describeRange(low: number | null, high: number | null): string {
  return low === null || high === null ? NOT_AVAILABLE : `${formatMw(low)} to ${formatMw(high)}`
}

export function ForecastBandChart({
  points,
  deliveryDayLabel,
  shouldShowActual,
}: ForecastBandChartProps) {
  const rows = buildDecisionChartData(points)
  const ticks = buildTimeTicks(
    rows.map((row) => row.timestamp),
    TIME_TICK_EVERY_HOURS,
  )
  const forecasts = points.map((point) => point.forecastMw)
  const highestMw = Math.max(
    ...rows.flatMap((row) => [
      row.forecastMw,
      row.band?.[1] ?? 0,
      shouldShowActual ? (row.actualMw ?? 0) : 0,
    ]),
  )
  const mwAxis = buildMwAxis(highestMw)
  const description =
    `Chart of forecast wind generation in MW for ${deliveryDayLabel}, ` +
    `from ${formatMw(Math.min(...forecasts))} to ${formatMw(Math.max(...forecasts))}.`
  const legendItems: LegendItem[] = [
    { label: 'Forecast', swatch: 'forecast' },
    { label: 'Typical range (P10 to P90)', swatch: 'band' },
  ]
  if (shouldShowActual) {
    legendItems.push({ label: 'Actual outturn', swatch: 'actual' })
  }

  return (
    <>
      <ChartLegend items={legendItems} />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <ComposedChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={ticks}
              tickFormatter={timestampToUkTime}
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Time of day (UK)')}
            />
            <YAxis
              domain={[0, mwAxis.max]}
              ticks={mwAxis.ticks}
              tickFormatter={formatThousands}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={Y_AXIS_WIDTH}
              label={yAxisLabel('MW')}
            />
            <Tooltip
              isAnimationActive={false}
              cursor={{ stroke: CHART_COLORS.axis }}
              content={tooltipContent<DecisionChartRow>((row) =>
                describeRow(row, shouldShowActual),
              )}
            />
            <Area
              dataKey="band"
              type="stepAfter"
              stroke="none"
              fill={CHART_COLORS.forecast}
              fillOpacity={0.16}
              activeDot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="forecastMw"
              type="stepAfter"
              stroke={CHART_COLORS.forecast}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            {shouldShowActual && (
              <Line
                dataKey="actualMw"
                type="linear"
                stroke={CHART_COLORS.actual}
                strokeWidth={2}
                strokeDasharray="6 4"
                dot={false}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <DataTableDisclosure
        caption={`Forecast wind generation for ${deliveryDayLabel}`}
        columns={['Time (UK)', 'Forecast', 'Typical range', 'Actual outturn']}
        rows={points.map((point) => [
          formatTimeUk(point.startTimeUtc),
          formatMw(point.forecastMw),
          describeRange(point.bandLowMw, point.bandHighMw),
          point.actualMw === null ? NOT_AVAILABLE : formatMw(point.actualMw),
        ])}
      />
    </>
  )
}
