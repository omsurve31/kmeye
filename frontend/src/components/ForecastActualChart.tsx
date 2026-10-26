import {
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX } from '../constants'
import type { SeriesPoint } from '../types/api'
import {
  buildDayTicks,
  buildMwAxis,
  buildSeriesChartData,
  type SeriesChartRow,
} from '../utils/chartData'
import {
  formatDayMonthUk,
  formatMw,
  formatSignedMw,
  formatThousands,
  formatTimeUk,
} from '../utils/format'
import { ChartLegend } from './ChartLegend'
import { tooltipContent } from './ChartTooltip'
import {
  AXIS_LINE,
  AXIS_TICK,
  CHART_MARGIN,
  X_AXIS_HEIGHT,
  Y_AXIS_WIDTH,
  xAxisLabel,
  yAxisLabel,
} from './chartStyle'

type ForecastActualChartProps = {
  points: SeriesPoint[]
}

function timestampToUkDay(timestamp: number): string {
  return formatDayMonthUk(new Date(timestamp).toISOString())
}

function describeRow(row: SeriesChartRow) {
  const iso = new Date(row.timestamp).toISOString()
  return {
    title: `${formatDayMonthUk(iso)}, ${formatTimeUk(iso)} UK time`,
    rows: [
      { label: 'Forecast', value: formatMw(row.forecastMw), swatch: 'forecast' as const },
      { label: 'Actual outturn', value: formatMw(row.actualMw), swatch: 'actual' as const },
      { label: 'Error (actual − forecast)', value: formatSignedMw(row.actualMw - row.forecastMw) },
    ],
  }
}

export function ForecastActualChart({ points }: ForecastActualChartProps) {
  const rows = buildSeriesChartData(points)
  const mwAxis = buildMwAxis(Math.max(...rows.flatMap((row) => [row.forecastMw, row.actualMw])))
  const first = points[0]
  const last = points[points.length - 1]
  const range =
    first && last
      ? `from ${formatDayMonthUk(first.startTimeUtc)} to ${formatDayMonthUk(last.startTimeUtc)}`
      : ''
  const description =
    `Chart of the forecast and the actual wind generation in MW for every half-hour ${range}. ` +
    'The table under the error-by-delivery-day chart gives daily numbers.'

  return (
    <>
      <ChartLegend
        items={[
          { label: 'Forecast', swatch: 'forecast' },
          { label: 'Actual outturn', swatch: 'actual' },
        ]}
      />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <ComposedChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="timestamp"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              ticks={buildDayTicks(rows.map((row) => row.timestamp))}
              tickFormatter={timestampToUkDay}
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Delivery day')}
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
              content={tooltipContent<SeriesChartRow>(describeRow)}
            />
            <Line
              dataKey="forecastMw"
              type="linear"
              stroke={CHART_COLORS.forecast}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="actualMw"
              type="linear"
              stroke={CHART_COLORS.actual}
              strokeWidth={1.5}
              strokeDasharray="6 4"
              dot={false}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
