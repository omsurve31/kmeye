import { CHART_COLORS } from '../constants'

// Shared look for every chart: quiet grid, muted axis text, labels in the axis colour.
export const CHART_MARGIN = { top: 8, right: 16, bottom: 8, left: 8 }
export const AXIS_TICK = { fill: CHART_COLORS.text, fontSize: 12 }
export const AXIS_LINE = { stroke: CHART_COLORS.axis }
export const Y_AXIS_WIDTH = 64
export const X_AXIS_HEIGHT = 44

export function yAxisLabel(text: string) {
  return {
    value: text,
    angle: -90,
    position: 'insideLeft' as const,
    fill: CHART_COLORS.text,
    fontSize: 12,
  }
}

export function xAxisLabel(text: string) {
  return {
    value: text,
    position: 'insideBottom' as const,
    offset: 0,
    fill: CHART_COLORS.text,
    fontSize: 12,
  }
}

// Show roughly `maxLabels` labels on a category axis by skipping the ones in between.
export function categoryInterval(count: number, maxLabels: number): number {
  return Math.max(0, Math.ceil(count / maxLabels) - 1)
}
