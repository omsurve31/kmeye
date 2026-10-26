import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { cloneElement, type ReactElement } from 'react'
import { afterEach, vi } from 'vitest'

// Vitest globals are off, so Testing Library cannot register its own cleanup.
afterEach(cleanup)

// jsdom has no layout, so Recharts' ResponsiveContainer would measure 0 x 0 and draw nothing.
// Give every chart a fixed size so tests can look at what it draws.
vi.mock('recharts', async (importOriginal) => {
  const actual = await importOriginal<typeof import('recharts')>()
  return {
    ...actual,
    ResponsiveContainer: ({
      children,
      height,
    }: {
      children: ReactElement<{ width: number; height: number }>
      height?: number
    }) => cloneElement(children, { width: 800, height: typeof height === 'number' ? height : 400 }),
  }
})
