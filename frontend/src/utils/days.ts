import { FIRST_DELIVERY_DAY, LAST_DELIVERY_DAY, MILLISECONDS_PER_DAY } from '../constants'

const DAY_PATTERN = /^\d{4}-\d{2}-\d{2}$/

function isRealDate(day: string): boolean {
  if (!DAY_PATTERN.test(day)) {
    return false
  }
  const parsed = new Date(`${day}T00:00:00Z`)
  // Round-tripping catches dates such as 2026-02-30 that JavaScript would roll over.
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(day)
}

// Days are "YYYY-MM-DD" strings, which sort in date order, so plain string comparison works.
export function isDeliveryDay(day: string): boolean {
  return isRealDate(day) && day >= FIRST_DELIVERY_DAY && day <= LAST_DELIVERY_DAY
}

export function shiftDay(day: string, deltaDays: number): string {
  const shifted = new Date(
    new Date(`${day}T00:00:00Z`).getTime() + deltaDays * MILLISECONDS_PER_DAY,
  )
  return shifted.toISOString().slice(0, 10)
}

export function clampToWindow(day: string): string {
  if (day < FIRST_DELIVERY_DAY) {
    return FIRST_DELIVERY_DAY
  }
  return day > LAST_DELIVERY_DAY ? LAST_DELIVERY_DAY : day
}
