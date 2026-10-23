import { describe, expect, it } from 'vitest'
import { formatValue, isAuditable, needsDisclosure } from './kpiDisplay'
import type { KpiMeasure } from '../../shared/types'

function measure(over: Partial<KpiMeasure> = {}): KpiMeasure {
  return {
    key: 'downtime_per_record',
    title: 'Downtime per record',
    value: 18.2,
    scale: 'hours',
    numerator: 91074,
    denominator: 5000,
    formula: 'sum(Downtime_Hours) / count(records)',
    population: 'every record',
    records: 5000,
    records_excluded: 0,
    records_unmeasured: 0,
    missing_policy: 'exclude',
    undefined_reason: null,
    edge_cases: '',
    ...over,
  }
}

describe('a controlled measure, as a reader sees it', () => {
  it('prints a percent on its own scale', () => {
    expect(formatValue(measure({ scale: 'percent', value: 76.56 }))).toBe('76.6%')
  })

  it('keeps Western digits in Arabic, as the rest of the interface does (ADR 0018)', () => {
    expect(formatValue(measure({ scale: 'percent', value: 77.01 }), 'ar')).toBe('77.0%')
    expect(formatValue(measure({ scale: 'money', value: 2410.41 }), 'ar')).toBe('2,410.41')
  })

  it('gives money two decimals, because a cent is a figure someone checks', () => {
    expect(formatValue(measure({ scale: 'money', value: 2513.14 }))).toBe('2,513.14')
  })

  // ADR 0042: an absence is not a zero. A card printing 0% here would be
  // claiming perfection from no evidence at all.
  it('refuses to print a number when nothing was measured', () => {
    const nothing = measure({ value: null, records: 0, undefined_reason: 'no record measured' })
    expect(formatValue(nothing)).toBeNull()
    expect(needsDisclosure(nothing)).toBe(true)
  })

  // ADR 0042's closing sentence: a card that hides the exclusions
  // re-creates the defect one layer up.
  it('demands disclosure when the figure rests on part of its population', () => {
    expect(needsDisclosure(measure({ records: 1, records_unmeasured: 1 }))).toBe(true)
    expect(needsDisclosure(measure())).toBe(false)
  })

  it('is auditable when the numerator over the records reproduces it', () => {
    expect(isAuditable(measure({ value: 18.2148, numerator: 91074, denominator: 5000 }))).toBe(true)
  })

  it('is not auditable when the arithmetic does not reproduce the figure', () => {
    expect(isAuditable(measure({ value: 99, numerator: 91074, denominator: 5000 }))).toBe(false)
  })

  it('reproduces a percent from its own two terms', () => {
    // first_time_fix is a ratio of sums over corrective orders. The value
    // is computed here rather than written out: a rounded literal is off by
    // more than the tolerance, which is the point of the tolerance.
    const numerator = 3074
    const denominator = 4015
    expect(isAuditable(measure({
      scale: 'percent',
      value: (numerator / denominator) * 100,
      numerator,
      denominator,
      records: denominator,
    }))).toBe(true)
  })

  it('rejects a figure rounded past the tolerance, rather than waving it through', () => {
    expect(isAuditable(measure({
      scale: 'percent', value: 76.5629, numerator: 3074, denominator: 4015, records: 4015,
    }))).toBe(false)
  })
})
