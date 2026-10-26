import { useCallback } from 'react'

import { getDecision } from '../api/client'
import type { Decision } from '../types/api'
import { useApiData } from './useApiData'

export function useDecisionData(day: string, cutoff: string) {
  const load = useCallback(
    (signal: AbortSignal): Promise<Decision> => getDecision({ day, cutoff }, signal),
    [day, cutoff],
  )
  return useApiData(load)
}
