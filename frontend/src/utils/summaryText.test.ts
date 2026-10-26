import { describe, expect, it } from 'vitest'

import { errorSummaryFixture } from '../test/fixtures'
import { buildBuyingSummary, describeBias } from './summaryText'

const context = { firstDay: '2026-01-02', lastDay: '2026-02-01', cutoffTimeUk: '09:00' }

describe('describeBias', () => {
  it('says the forecast was higher than the outturn when the bias is negative', () => {
    expect(describeBias(-1747.9)).toBe(
      'On average the forecast was 1,748 MW higher than the outturn.',
    )
  })

  it('says the forecast was lower than the outturn when the bias is positive', () => {
    expect(describeBias(310.2)).toBe('On average the forecast was 310 MW lower than the outturn.')
  })

  it('says the forecast matched the outturn when the bias rounds to zero', () => {
    expect(describeBias(0.3)).toBe('On average the forecast matched the outturn.')
  })
})

describe('buildBuyingSummary', () => {
  it('states how close 90% of half-hours finished to the forecast', () => {
    const [first] = buildBuyingSummary(errorSummaryFixture, context)

    expect(first).toBe(
      'In 90% of half-hours between 2 Jan 2026 and 1 Feb 2026, the actual outturn finished within ' +
        '3,900 MW of the forecast available at the 09:00 UK cutoff.',
    )
  })

  it('states how often and how far the forecast was too high', () => {
    const lines = buildBuyingSummary(errorSummaryFixture, context)

    expect(lines[1]).toBe(
      'The forecast was too high in 84.7% of half-hours. In 10% of half-hours it was too high by ' +
        'more than 4,140 MW, a shortfall the buyer would have had to cover.',
    )
  })

  it('describes a rarely-high forecast when the 10th percentile error is not negative', () => {
    const lines = buildBuyingSummary(
      { ...errorSummaryFixture, errorP10Mw: 25, overForecastFraction: 0.05 },
      context,
    )

    expect(lines[1]).toBe('The forecast was too high in only 5.0% of half-hours.')
  })

  it('includes the bias sentence and the backward-looking caveat', () => {
    const lines = buildBuyingSummary(errorSummaryFixture, context)

    expect(lines[2]).toBe('On average the forecast was 1,748 MW higher than the outturn.')
    expect(lines[3]).toBe(
      'This is backward-looking evidence from January 2026 decisions, not a guarantee of future accuracy.',
    )
  })
})
