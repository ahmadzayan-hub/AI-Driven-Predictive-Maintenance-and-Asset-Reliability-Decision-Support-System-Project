import { describe, expect, it } from 'vitest'
import { dailyStarts, greetingKey } from './summary'
import type { RunSummary } from '../../shared/types'

const run = (created_at: string): RunSummary => ({ id: created_at, goal: 'Synthetic', dataset_name: 'Synthetic', state: 'completed', created_at, updated_at: created_at })

describe('the brief counts starts by day', () => {
  const today = new Date('2026-10-27T15:00:00Z')
  it('places each run on its UTC day, oldest first, and counts the period before', () => {
    const runs = [run('2026-10-27T01:00:00Z'), run('2026-10-27T23:30:00Z'), run('2026-10-20T09:00:00Z'),
      run('2026-10-14T00:00:00Z'), run('2026-10-13T23:59:59Z'), run('2026-09-30T00:00:00Z'), run('not a date')]
    const trend = dailyStarts(runs, 14, today)
    expect(trend.counts).toHaveLength(14)
    expect(trend.counts[13]).toBe(2)
    expect(trend.counts[6]).toBe(1)
    expect(trend.counts[0]).toBe(1) // 14 October is the first day of the window
    expect(trend.total).toBe(4)
    expect(trend.previous).toBe(2) // 13 October and 30 September; the unreadable date is left out
  })
  it('is all zeros with no runs, never undefined', () => {
    expect(dailyStarts([], 7, today)).toEqual({ counts: [0, 0, 0, 0, 0, 0, 0], total: 0, previous: 0 })
  })
  it('greets by the hour', () => {
    expect([greetingKey(0), greetingKey(11), greetingKey(12), greetingKey(17), greetingKey(18), greetingKey(23)])
      .toEqual(['morning', 'morning', 'afternoon', 'afternoon', 'evening', 'evening'])
  })
})
