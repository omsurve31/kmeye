import { getMeta } from '../api/client'
import { useApiData } from './useApiData'

export function useMeta() {
  return useApiData(getMeta)
}
