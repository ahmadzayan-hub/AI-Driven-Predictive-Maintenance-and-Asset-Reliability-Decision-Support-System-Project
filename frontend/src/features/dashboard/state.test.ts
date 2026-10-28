import { describe, expect, it } from 'vitest'
import { EMPTY, isPicked, isRangePicked, pick, pickRange, readState, writeState } from './state'

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

describe('pickRange', () => {
  it('keeps one histogram bin as the measure range, and releases it on the second click', () => {
    const kept = pickRange({ ...EMPTY, offset: 50 }, 10, 20, false)
    expect(kept).toMatchObject({ lo: 10, hi: 20, hiop: 'lt', offset: 0 })
    expect(isRangePicked(kept, 10, 20, false)).toBe(true)
    expect(isRangePicked(kept, 20, 30, false)).toBe(false)
    expect(writeState(kept)).toBe('lo=10&hi=20&hiop=lt')
    const released = pickRange(kept, 10, 20, false)
    expect(released).toMatchObject({ lo: null, hi: null, hiop: 'lte' })
  })

  it('includes the upper edge of the last bin', () => {
    const last = pickRange(EMPTY, 90, 100, true)
    expect(last.hiop).toBe('lte')
    expect(isRangePicked(last, 90, 100, true)).toBe(true)
    expect(isRangePicked(last, 90, 100, false)).toBe(false)
  })
})
