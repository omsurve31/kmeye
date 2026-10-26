import { useId, type ChangeEvent } from 'react'

import { FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY } from '../constants'
import { isDeliveryDay } from '../utils/days'

export type DayRange = {
  from: string
  to: string
}

type DateRangeControlProps = DayRange & {
  onChange: (range: DayRange) => void
}

export function DateRangeControl({ from, to, onChange }: DateRangeControlProps) {
  const fromId = useId()
  const toId = useId()
  const isWholeWindow = from === FIRST_DELIVERY_DAY && to === LAST_DELIVERY_DAY

  // Setting one end past the other drags the other end with it, so the range is never backwards.
  const handleFromChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value
    if (isDeliveryDay(value)) {
      onChange({ from: value, to: value > to ? value : to })
    }
  }

  const handleToChange = (event: ChangeEvent<HTMLInputElement>) => {
    const value = event.target.value
    if (isDeliveryDay(value)) {
      onChange({ from: value < from ? value : from, to: value })
    }
  }

  return (
    <div className="control">
      <span className="control__label">Delivery days</span>
      <div className="control__row">
        <label htmlFor={fromId} className="control__inline-label">
          From
        </label>
        <input
          id={fromId}
          className="input"
          type="date"
          min={FIRST_DELIVERY_DAY}
          max={LAST_DELIVERY_DAY}
          value={from}
          onChange={handleFromChange}
        />
        <label htmlFor={toId} className="control__inline-label">
          To
        </label>
        <input
          id={toId}
          className="input"
          type="date"
          min={FIRST_DELIVERY_DAY}
          max={LAST_DELIVERY_DAY}
          value={to}
          onChange={handleToChange}
        />
        <button
          type="button"
          className="button button--quiet"
          disabled={isWholeWindow}
          onClick={() => onChange({ from: FIRST_DELIVERY_DAY, to: LAST_DELIVERY_DAY })}
        >
          Whole window
        </button>
      </div>
    </div>
  )
}
