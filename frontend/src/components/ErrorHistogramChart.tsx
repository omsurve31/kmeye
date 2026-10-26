import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CHART_COLORS, CHART_HEIGHT_PX } from '../constants'
import type { ErrorSummary, HistogramBin } from '../types/api'
import { buildHistogramRows, type HistogramRow } from '../utils/chartData'
import { formatSignedMw, formatThousands } from '../utils/format'
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

type ErrorHistogramChartProps = {
  bins: HistogramBin[]
  summary: ErrorSummary
}

const MAX_X_LABELS = 8
const DIRECTION_TEXT = {
  'over-forecast': 'Forecast too high',
  'under-forecast': 'Forecast too low',
}

function describeRow(row: HistogramRow) {
  return {
    title: row.label,
    rows: [
      {
        label: DIRECTION_TEXT[row.direction],
        value: `${formatThousands(row.count)} half-hours`,
        swatch: row.direction === 'over-forecast' ? ('over' as const) : ('under' as const),
      },
    ],
  }
}

export function ErrorHistogramChart({ bins, summary }: ErrorHistogramChartProps) {
  const rows = buildHistogramRows(bins)
  const description =
    'Histogram of forecast errors in MW. Bars to the left are half-hours where the forecast was ' +
    `too high. The middle 80% of errors ran from ${formatSignedMw(summary.errorP10Mw)} to ` +
    `${formatSignedMw(summary.errorP90Mw)}.`

  return (
    <>
      <ChartLegend
        items={[
          { label: 'Forecast too high (error below 0)', swatch: 'over' },
          { label: 'Forecast too low (error 0 or above)', swatch: 'under' },
        ]}
      />
      <div className="chart-frame" role="img" aria-label={description}>
        <ResponsiveContainer width="100%" height={CHART_HEIGHT_PX}>
          <BarChart data={rows} margin={CHART_MARGIN} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
            <XAxis
              dataKey="binStartMw"
              tickFormatter={formatThousands}
              interval={categoryInterval(rows.length, MAX_X_LABELS)}
              tick={AXIS_TICK}
              axisLine={AXIS_LINE}
              tickLine={AXIS_LINE}
              height={X_AXIS_HEIGHT}
              label={xAxisLabel('Error (actual − forecast), MW')}
            />
            <YAxis
              tickFormatter={formatThousands}
              tick={AXIS_TICK}
              axisLine={false}
              tickLine={false}
              width={Y_AXIS_WIDTH}
              label={yAxisLabel('Half-hours')}
            />
            <Tooltip
              isAnimationActive={false}
              cursor={{ fill: CHART_COLORS.grid }}
              content={tooltipContent<HistogramRow>(describeRow)}
            />
            <Bar dataKey="count" radius={[2, 2, 0, 0]} isAnimationActive={false}>
              {rows.map((row) => (
                <Cell
                  key={row.binStartMw}
                  fill={
                    row.direction === 'over-forecast'
                      ? CHART_COLORS.overForecast
                      : CHART_COLORS.underForecast
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <DataTableDisclosure
        caption="Number of half-hours by size of forecast error"
        columns={['Error range', 'Half-hours']}
        rows={rows.map((row) => [row.label, formatThousands(row.count)])}
      />
    </>
  )
}
