import { useCallback } from 'react'

import {
  getAccuracySeries,
  getAccuracySummary,
  getDailyAccuracy,
  getDistribution,
  getHorizonAccuracy,
  getHourlyAccuracy,
} from '../api/client'
import type {
  AccuracySeries,
  AccuracySummary,
  DailyAccuracy,
  Distribution,
  HorizonAccuracy,
  HourlyAccuracy,
} from '../types/api'
import { useApiData } from './useApiData'

export type AccuracyData = {
  summary: AccuracySummary
  series: AccuracySeries
  hourly: HourlyAccuracy
  daily: DailyAccuracy
  distribution: Distribution
  horizon: HorizonAccuracy
}

// The view needs all six datasets, so they load together: the page shows one loading state and
// one error state instead of six.
export function useAccuracyData(from: string, to: string, cutoff: string) {
  const load = useCallback(
    async (signal: AbortSignal): Promise<AccuracyData> => {
      const query = { from, to, cutoff }
      const [summary, series, hourly, daily, distribution, horizon] = await Promise.all([
        getAccuracySummary(query, signal),
        getAccuracySeries(query, signal),
        getHourlyAccuracy(query, signal),
        getDailyAccuracy(query, signal),
        getDistribution(query, signal),
        getHorizonAccuracy({ from, to }, signal),
      ])
      return { summary, series, hourly, daily, distribution, horizon }
    },
    [from, to, cutoff],
  )
  return useApiData(load)
}
