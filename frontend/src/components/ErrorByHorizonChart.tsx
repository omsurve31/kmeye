import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX } from '../constants'
import type { HorizonErrors } from '../types/api'
import { buildHorizonRows, type HorizonRow } from '../utils/chartData'
import { formatMw, formatThousands } from '../utils/format'
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
import { DataTableDisclosure } from './DataTableDisclosure'

type ErrorByHorizonChartProps = {
  horizons: HorizonErrors[]
}

function describeRow(row: HorizonRow) {
  return {
    title: `Published ${row.label} before the target hour`,
    rows: [
      { label: 'Mean absolute error', value: formatMw(row.maeMw), swatch: 'magnitude' as const },
    ],
  }
}

export function ErrorByHorizonChart({ horizons }: ErrorByHorizonChartProps) {
  const rows = buildHorizonRows(horizons)
  const description =
    'Bar chart of the mean absolute error in MW by how many hours before the target hour the ' +
    'forecast was published.'

  return (
    <>
      <ChartLegend items={[{ label: 'Mean absolute error', swatch: 'magnitude' }]} />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <BarChart data={rows} margin={CHART_MARGIN}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="label"
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Hours between publication and target hour')}
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
              content={tooltipContent<HorizonRow>(describeRow)}
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
        caption="Mean absolute error by forecast lead time"
        columns={['Published before target', 'Mean absolute error']}
        rows={rows.map((row) => [row.label, formatMw(row.maeMw)])}
      />
    </>
  )
}
