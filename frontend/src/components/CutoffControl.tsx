import { useId, type ChangeEvent } from 'react'

import { FORECAST_PUBLISH_TIMES_UK, HOURS_PER_DAY } from '../constants'

type CutoffControlProps = {
  cutoff: string
  onChange: (cutoff: string) => void
}

const HOURS = Array.from({ length: HOURS_PER_DAY }, (_value, hour) => String(hour).padStart(2, '0'))
const QUARTER_HOUR_MINUTES = ['00', '15', '30', '45']

// The cutoff is picked as an hour and a minute (24-hour, UK time). The browser's own time input
// shows AM/PM on some computers, which would clash with the 24-hour times used everywhere else.
export function CutoffControl({ cutoff, onChange }: CutoffControlProps) {
  const hourId = useId()
  const minuteId = useId()
  const [hour = '09', minute = '00'] = cutoff.split(':')
  const minuteOptions = QUARTER_HOUR_MINUTES.includes(minute)
    ? QUARTER_HOUR_MINUTES
    : [...QUARTER_HOUR_MINUTES, minute].sort()

  const handleHourChange = (event: ChangeEvent<HTMLSelectElement>) =>
    onChange(`${event.target.value}:${minute}`)
  const handleMinuteChange = (event: ChangeEvent<HTMLSelectElement>) =>
    onChange(`${hour}:${event.target.value}`)

  return (
    <fieldset className="control control--group">
      <legend className="control__label">Decision cutoff (UK time)</legend>
      <div className="control__row">
        <label htmlFor={hourId} className="visually-hidden">
          Hour
        </label>
        <select id={hourId} className="input" value={hour} onChange={handleHourChange}>
          {HOURS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <span aria-hidden="true">:</span>
        <label htmlFor={minuteId} className="visually-hidden">
          Minute
        </label>
        <select id={minuteId} className="input" value={minute} onChange={handleMinuteChange}>
          {minuteOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      </div>
      <p className="control__hint">
        Assumes the buyer decides at this time on the day before delivery and sees the latest
        forecast published before this time. Elexon publishes new forecasts at{' '}
        {FORECAST_PUBLISH_TIMES_UK.join(', ')} UK time.
      </p>
    </fieldset>
  )
}
