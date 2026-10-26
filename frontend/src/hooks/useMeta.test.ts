import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { getMeta } from '../api/client'
import { metaFixture } from '../test/fixtures'
import { useMeta } from './useMeta'

vi.mock('../api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../api/client')>()),
  getMeta: vi.fn(),
}))

describe('useMeta', () => {
  it('loads the data description once', async () => {
    vi.mocked(getMeta).mockResolvedValue(metaFixture)

    const { result } = renderHook(() => useMeta())

    await waitFor(() =>
      expect(result.current.state).toEqual({ status: 'success', data: metaFixture }),
    )
    expect(getMeta).toHaveBeenCalledTimes(1)
  })
})
