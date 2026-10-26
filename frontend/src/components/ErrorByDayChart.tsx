import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX } from '../constants'
import type { DayErrors } from '../types/api'
import { buildDayRows, type DayRow } from '../utils/chartData'
import { formatDayLabel, formatMw, formatThousands } from '../utils/format'
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

type ErrorByDayChartProps = {
  days: DayErrors[]
}

const MAX_X_LABELS = 8

function describeRow(row: DayRow) {
  return {
    title: formatDayLabel(row.day),
    rows: [
      { label: 'Mean absolute error', value: formatMw(row.maeMw), swatch: 'magnitude' as const },
    ],
  }
}

export function ErrorByDayChart({ days }: ErrorByDayChartProps) {
  const rows = buildDayRows(days)
  const worst = rows.reduce((current, row) => (row.maeMw > current.maeMw ? row : current), rows[0])
  const description =
    'Bar chart of the mean absolute error in MW for each delivery day.' +
    (worst ? ` The largest error is on ${worst.label}, ${formatMw(worst.maeMw)}.` : '')

  return (
    <>
      <ChartLegend items={[{ label: 'Mean absolute error', swatch: 'magnitude' }]} />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <BarChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="label"
              interval={categoryInterval(rows.length, MAX_X_LABELS)}
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Delivery day')}
            />
            <YAxis
              tickFormatter={formatThousands}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={Y_AXIS_WIDTH}
              label={yAxisLabel('MW')}
            />
            <Tooltip
              isAnimationActive={false}
              cursor={{ fill: CHART_COLORS.grid }}
              content={tooltipContent<DayRow>(describeRow)}
            />
            <Bar
              dataKey="maeMw"
              fill={CHART_COLORS.magnitude}
              radius={[2, 2, 0, 0]}
              isAnimationActive={false}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTableDisclosure
        caption="Mean absolute error by delivery day"
        columns={['Delivery day', 'Mean absolute error']}
        rows={rows.map((row) => [formatDayLabel(row.day), formatMw(row.maeMw)])}
      />
    </>
  )
}
