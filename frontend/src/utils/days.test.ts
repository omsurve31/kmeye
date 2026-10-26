import { describe, expect, it } from 'vitest'

import { clampToWindow, isDeliveryDay, shiftDay } from './days'

describe('shiftDay', () => {
  it('moves forward across a month end', () => {
    expect(shiftDay('2026-01-31', 1)).toBe('2026-02-01')
  })

  it('moves backward across a month start', () => {
    expect(shiftDay('2026-02-01', -1)).toBe('2026-01-31')
  })

  it('moves by several days', () => {
    expect(shiftDay('2026-01-02', 7)).toBe('2026-01-09')
  })
})

describe('isDeliveryDay', () => {
  it.each(['2026-01-02', '2026-01-15', '2026-02-01'])('accepts %s', (day) => {
    expect(isDeliveryDay(day)).toBe(true)
  })

  it.each(['2026-01-01', '2026-02-02', '2025-12-31', 'oops', '', '2026-1-5', '2026-01-32'])(
    'rejects %s',
    (day) => {
      expect(isDeliveryDay(day)).toBe(false)
    },
  )
})

describe('clampToWindow', () => {
  it('keeps a day that is already inside the window', () => {
    expect(clampToWindow('2026-01-10')).toBe('2026-01-10')
  })

  it('moves a day before the window to the first delivery day', () => {
    expect(clampToWindow('2025-12-01')).toBe('2026-01-02')
  })

  it('moves a day after the window to the last delivery day', () => {
    expect(clampToWindow('2026-03-01')).toBe('2026-02-01')
  })
})
