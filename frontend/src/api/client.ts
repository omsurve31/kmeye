import { API_BASE_PATH } from '../constants'
import type {
  AccuracySeries,
  AccuracySummary,
  DailyAccuracy,
  Decision,
  Distribution,
  HorizonAccuracy,
  HourlyAccuracy,
  Meta,
} from '../types/api'

export type ApiErrorKind = 'validation' | 'not-found' | 'unavailable' | 'network' | 'unexpected'

const NOT_FOUND_MESSAGE = 'No data is available for this selection.'
const VALIDATION_MESSAGE = 'The request was not valid.'
const UNAVAILABLE_MESSAGE =
  'The forecast data is temporarily unavailable. Please try again shortly.'
const NETWORK_MESSAGE = 'Could not reach the server. Check your connection and try again.'
const UNEXPECTED_MESSAGE = 'Something went wrong while loading the data.'

export class ApiError extends Error {
  readonly kind: ApiErrorKind
  readonly status: number | null

  constructor(kind: ApiErrorKind, message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
  }
}

export type DecisionQuery = { day: string; cutoff: string }
export type RangeQuery = { from: string; to: string }
export type AccuracyQuery = RangeQuery & { cutoff: string }

function snakeToCamel(key: string): string {
  return key.replace(/_([a-z0-9])/g, (_match, character: string) => character.toUpperCase())
}

// The backend speaks snake_case; the rest of the app speaks camelCase. This is the only place
// that converts between them.
function camelizeKeys(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(camelizeKeys)
  }
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, inner]) => [snakeToCamel(key), camelizeKeys(inner)]),
    )
  }
  return value
}

function buildUrl(path: string, params: Record<string, string>): string {
  const query = new URLSearchParams(params).toString()
  return query ? `${API_BASE_PATH}${path}?${query}` : `${API_BASE_PATH}${path}`
}

async function readErrorDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json()
    if (typeof body === 'object' && body !== null && 'detail' in body) {
      return typeof body.detail === 'string' ? body.detail : null
    }
  } catch {
    return null
  }
  return null
}

async function toApiError(response: Response): Promise<ApiError> {
  const detail = await readErrorDetail(response)
  switch (response.status) {
    case 422:
      return new ApiError('validation', detail ?? VALIDATION_MESSAGE, 422)
    case 404:
      return new ApiError('not-found', detail ?? NOT_FOUND_MESSAGE, 404)
    case 503:
      return new ApiError('unavailable', UNAVAILABLE_MESSAGE, 503)
    default:
      // Other failures may carry internal details, so they are not shown to the user.
      return new ApiError('unexpected', UNEXPECTED_MESSAGE, response.status)
  }
}

async function getJson<T>(
  path: string,
  params: Record<string, string>,
  signal?: AbortSignal,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(buildUrl(path, params), { signal })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    throw new ApiError('network', NETWORK_MESSAGE)
  }
  if (!response.ok) {
    throw await toApiError(response)
  }
  try {
    return camelizeKeys(await response.json()) as T
  } catch {
    throw new ApiError('unexpected', UNEXPECTED_MESSAGE, response.status)
  }
}

export function getMeta(signal?: AbortSignal): Promise<Meta> {
  return getJson<Meta>('/meta', {}, signal)
}

export function getDecision(query: DecisionQuery, signal?: AbortSignal): Promise<Decision> {
  return getJson<Decision>('/decision', { day: query.day, cutoff: query.cutoff }, signal)
}

function accuracyParams(query: AccuracyQuery): Record<string, string> {
  return { from: query.from, to: query.to, cutoff: query.cutoff }
}

export function getAccuracySummary(
  query: AccuracyQuery,
  signal?: AbortSignal,
): Promise<AccuracySummary> {
  return getJson<AccuracySummary>('/accuracy/summary', accuracyParams(query), signal)
}

export function getAccuracySeries(
  query: AccuracyQuery,
  signal?: AbortSignal,
): Promise<AccuracySeries> {
  return getJson<AccuracySeries>('/accuracy/series', accuracyParams(query), signal)
}

export function getHourlyAccuracy(
  query: AccuracyQuery,
  signal?: AbortSignal,
): Promise<HourlyAccuracy> {
  return getJson<HourlyAccuracy>('/accuracy/by-hour', accuracyParams(query), signal)
}

export function getDailyAccuracy(
  query: AccuracyQuery,
  signal?: AbortSignal,
): Promise<DailyAccuracy> {
  return getJson<DailyAccuracy>('/accuracy/by-day', accuracyParams(query), signal)
}

export function getDistribution(query: AccuracyQuery, signal?: AbortSignal): Promise<Distribution> {
  return getJson<Distribution>('/accuracy/distribution', accuracyParams(query), signal)
}

export function getHorizonAccuracy(
  query: RangeQuery,
  signal?: AbortSignal,
): Promise<HorizonAccuracy> {
  return getJson<HorizonAccuracy>(
    '/accuracy/by-horizon',
    { from: query.from, to: query.to },
    signal,
  )
}
