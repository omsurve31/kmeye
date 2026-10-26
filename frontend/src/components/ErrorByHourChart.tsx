import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX } from '../constants'
import type { HourOfDayErrors } from '../types/api'
import { buildHourRows, type HourRow } from '../utils/chartData'
import { formatMw, formatSignedMw, formatThousands } from '../utils/format'
import { ChartLegend } from './ChartLegend'
import { tooltipContent } from './ChartTooltip'
import {
  AXIS_LINE,
  AXIS_TICK,
  CHART_MARGIN,
  X_AXIS_HEIGHT,
  Y_AXIS_WIDTH,
  categoryInterval,
  xAxisLabel,
  yAxisLabel,
} from './chartStyle'
import { DataTableDisclosure } from './DataTableDisclosure'

type ErrorByHourChartProps = {
  hours: HourOfDayErrors[]
}

const MAX_X_LABELS = 8

function describeRow(row: HourRow) {
  return {
    title: `${row.label} UK time`,
    rows: [
      {
        label: 'Mean absolute error',
        value: formatMw(row.maeMw),
        swatch: 'magnitude' as const,
      },
      {
        label: 'Bias (negative = too high)',
        value: formatSignedMw(row.biasMw),
        swatch: 'over' as const,
      },
    ],
  }
}

export function ErrorByHourChart({ hours }: ErrorByHourChartProps) {
  const rows = buildHourRows(hours)
  const worst = rows.reduce((current, row) => (row.maeMw > current.maeMw ? row : current), rows[0])
  const description =
    'Chart of the mean absolute error and the bias in MW for each UK hour of the day.' +
    (worst ? ` The largest average error is at ${worst.label}, ${formatMw(worst.maeMw)}.` : '')

  return (
    <>
      <ChartLegend
        items={[
          { label: 'Mean absolute error', swatch: 'magnitude' },
          { label: 'Bias (below 0: forecast too high)', swatch: 'over' },
        ]}
      />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <ComposedChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="label"
              interval={categoryInterval(rows.length, MAX_X_LABELS)}
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Hour of day (UK)')}
            />
            <YAxis
              tickFormatter={formatThousands}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={Y_AXIS_WIDTH}
              label={yAxisLabel('MW')}
            />
            <ReferenceLine y={0} stroke={CHART_COLORS.axis} />
            <Tooltip
              isAnimationActive={false}
              cursor={{ fill: CHART_COLORS.grid }}
              content={tooltipContent<HourRow>(describeRow)}
            />
            <Bar
              dataKey="maeMw"
              fill={CHART_COLORS.magnitude}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
            <Line
              dataKey="biasMw"
              type="monotone"
              stroke={CHART_COLORS.overForecast}
              strokeWidth={2}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <DataTableDisclosure
        caption="Forecast error by UK hour of the day"
        columns={['Hour (UK)', 'Mean absolute error', 'Bias']}
        rows={rows.map((row) => [row.label, formatMw(row.maeMw), formatSignedMw(row.biasMw)])}
      />
    </>
  )
}
