import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'
import { APP_SUBTITLE, APP_TITLE } from './constants'

describe('App', () => {
  it('renders the portal title as the main heading', () => {
    render(<App />)

    expect(screen.getByRole('heading', { level: 1, name: APP_TITLE })).toBeInTheDocument()
  })

  it('renders the portal subtitle', () => {
    render(<App />)

    expect(screen.getByText(APP_SUBTITLE)).toBeInTheDocument()
  })
})
