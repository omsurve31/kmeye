import { useId, type ChangeEvent } from 'react'

import { FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY } from '../constants'
import { isDeliveryDay, shiftDay } from '../utils/days'
import { formatDayLabel } from '../utils/format'
import { ChevronIcon } from './ChevronIcon'

type DayPickerProps = {
  day: string
  onChange: (day: string) => void
}

export function DayPicker({ day, onChange }: DayPickerProps) {
  const inputId = useId()

  // The browser date input can be cleared or typed past the window; only real delivery days count.
  const handleInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (isDeliveryDay(event.target.value)) {
      onChange(event.target.value)
    }
  }

  return (
    <div className="control">
      <label htmlFor={inputId} className="control__label">
        Delivery day
      </label>
      <div className="control__row">
        <button
          type="button"
          className="icon-button"
          aria-label="Previous day"
          disabled={day <= FIRST_DELIVERY_DAY}
          onClick={() => onChange(shiftDay(day, -1))}
        >
          <ChevronIcon direction="left" />
        </button>
        <input
          id={inputId}
          className="input"
          type="date"
          min={FIRST_DELIVERY_DAY}
          max={LAST_DELIVERY_DAY}
          value={day}
          onChange={handleInputChange}
        />
        <button
          type="button"
          className="icon-button"
          aria-label="Next day"
          disabled={day >= LAST_DELIVERY_DAY}
          onClick={() => onChange(shiftDay(day, 1))}
        >
          <ChevronIcon direction="right" />
        </button>
      </div>
      <p className="control__hint">{formatDayLabel(day)}</p>
    </div>
  )
}
