export const APP_TITLE = 'UK Wind Forecast Portal'
export const APP_SUBTITLE = 'Day-ahead wind forecasts and how accurate they have been'

export const API_BASE_PATH = '/api'

// Scope: decisions made in January 2026, so delivery days 2 Jan to 1 Feb 2026.
export const FIRST_DELIVERY_DAY = '2026-01-02'
export const LAST_DELIVERY_DAY = '2026-02-01'
export const DEFAULT_DECISION_DAY = '2026-01-15'

// Assumption: the buyer decides at this UK time on the day before delivery.
export const DEFAULT_CUTOFF_TIME_UK = '09:00'
export const UK_TIMEZONE = 'Europe/London'

// Times (UK, winter) at which Elexon publishes a new wind forecast. Shown as a hint next to the cutoff.
export const FORECAST_PUBLISH_TIMES_UK = [
  '02:30',
  '04:30',
  '07:30',
  '09:30',
  '11:30',
  '15:30',
  '18:30',
  '22:30',
]

export const ERROR_SIGN_NOTE =
  'Error = actual − forecast. A negative error means the forecast was too high (over-forecast), ' +
  'so the buyer is short. A positive error means it was too low (surplus wind).'

// Charts. Colours come from CSS variables so light and dark mode can use different steps.
export const CHART_COLORS = {
  forecast: 'var(--chart-forecast)',
  actual: 'var(--chart-actual)',
  magnitude: 'var(--chart-magnitude)',
  overForecast: 'var(--chart-over)',
  underForecast: 'var(--chart-under)',
  grid: 'var(--chart-grid)',
  axis: 'var(--chart-axis)',
  text: 'var(--chart-text)',
} as const
// Round steps for the MW axis of the time-series charts, tried smallest first.
export const NICE_MW_STEPS = [500, 1000, 2000, 2500, 4000, 5000, 10000]
export const MAX_MW_AXIS_STEPS = 5
export const CHART_HEIGHT_PX = 340
export const TIME_TICK_EVERY_HOURS = 3
export const MAX_DAY_TICKS = 8

export const HOURS_PER_DAY = 24
export const MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000
