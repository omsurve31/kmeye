import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LoadingState } from './LoadingState'

describe('LoadingState', () => {
  it('tells assistive technology what is loading', () => {
    render(<LoadingState label="the forecast" />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading the forecast…')
  })
})
