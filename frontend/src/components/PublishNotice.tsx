import { formatPublishedAt } from '../utils/format'

type PublishNoticeProps = {
  publishTimesUtc: string[]
}

// The buyer must know which forecast they are looking at, so this is always shown above the numbers.
export function PublishNotice({ publishTimesUtc }: PublishNoticeProps) {
  const first = publishTimesUtc[0]
  const last = publishTimesUtc[publishTimesUtc.length - 1]
  if (first === undefined || last === undefined) {
    return null
  }
  if (first === last) {
    return (
      <p className="publish-notice">
        Based on the forecast published at <strong>{formatPublishedAt(first)}</strong>
      </p>
    )
  }
  return (
    <p className="publish-notice">
      Based on forecasts published between <strong>{formatPublishedAt(first)}</strong> and{' '}
      <strong>{formatPublishedAt(last)}</strong>
    </p>
  )
}
