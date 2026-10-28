import { describe, expect, it } from 'vitest'
import { EMPTY, isPicked, pick, readState, writeState } from './state'

// Cross-filtering by clicking (ADR 2026-10-27-interactive-dashboard): a click
// keeps one group alone in the address, a second click on it releases it,
// and a period is kept as a from/to range.
describe('pick', () => {
  it('keeps the clicked group alone and releases it on the second click', () => {
    const kept = pick({ ...EMPTY, offset: 25 }, 'region', 'North', 'month')
    expect(kept.filters).toEqual({ region: ['North'] })
    expect(kept.offset).toBe(0)
    expect(isPicked(kept, 'region', 'North', 'month')).toBe(true)
    expect(isPicked(kept, 'region', 'South', 'month')).toBe(false)
    expect(writeState(kept)).toBe('f.region=North')
    expect(pick(kept, 'region', 'North', 'month').filters).toEqual({})
  })

  it('replaces a wider selection of the same column and leaves other columns alone', () => {
    const state = readState('f.region=North&f.region=South&f.category=Software')
    expect(isPicked(state, 'region', 'North', 'month')).toBe(false)
    const kept = pick(state, 'region', 'North', 'month')
    expect(kept.filters).toEqual({ region: ['North'], category: ['Software'] })
  })

  it('keeps a clicked period as a range of one period', () => {
    const kept = pick(EMPTY, 'month', '2025-03', 'month')
    expect(kept.from).toBe('2025-03')
    expect(kept.to).toBe('2025-03')
    expect(isPicked(kept, 'month', '2025-03', 'month')).toBe(true)
    expect(writeState(kept)).toBe('from=2025-03&to=2025-03')
    const released = pick(kept, 'month', '2025-03', 'month')
    expect(released.from).toBeNull()
    expect(released.to).toBeNull()
  })
})
