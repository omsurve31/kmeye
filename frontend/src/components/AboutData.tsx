import type { Meta } from '../types/api'
import { formatShortDate, formatThousands } from '../utils/format'

type AboutDataProps = {
  meta: Meta
}

export function AboutData({ meta }: AboutDataProps) {
  const { forecastSummary, actualSummary } = meta
  return (
    <details className="about">
      <summary>About this data</summary>
      <ul className="about__list">
        <li>
          Source: Elexon Insights API, national wind generation only. Actual outturn is the FUELHH
          dataset (half-hourly); the forecast is WINDFOR (hourly, published eight times a day).
        </li>
        <li>
          Scope: purchase decisions made in January 2026, so delivery days{' '}
          {formatShortDate(meta.firstDeliveryDay)} to {formatShortDate(meta.lastDeliveryDay)}.
        </li>
        <li>
          An hourly forecast is applied to both half-hours of its hour when it is compared with the
          half-hourly actual.
        </li>
        <li>{meta.errorDefinition}</li>
        <li>
          Kept {formatThousands(forecastSummary.rowsKept)} of{' '}
          {formatThousands(forecastSummary.rowsFetched)} forecast rows and{' '}
          {formatThousands(actualSummary.rowsKept)} of {formatThousands(actualSummary.rowsFetched)}{' '}
          actual half-hours. Forecasts published after their target hour began are not used.
        </li>
        {meta.missingActualHalfHours > 0 && (
          <li>{meta.missingActualHalfHours} half-hours have no actual value.</li>
        )}
        <li>
          Forecast and outturn come from different Elexon datasets, so a steady gap between them can
          partly reflect how each is defined rather than forecaster skill.
        </li>
      </ul>
    </details>
  )
}
