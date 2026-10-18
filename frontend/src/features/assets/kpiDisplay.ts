import type { KpiMeasure } from '../../shared/types'

/** How a controlled measure is written for a reader.
 *
 *  Two rules, both from ADR 0042 and restated by ADR 0049.
 *
 *  A measure with no evidence is not a zero. When `value` is null the
 *  register has said why in `undefined_reason`, and a card must print that
 *  absence rather than a number, because `0%` claims perfection from
 *  nothing at all.
 *
 *  A measure computed on part of its population must say so. When
 *  `records_unmeasured` is non-zero the figure rests on fewer records than
 *  the population holds, and hiding that re-creates the defect one layer
 *  up — which is the sentence ADR 0042 ends on.
 */

/** Whether the reader must be told something about this figure's evidence. */
export function needsDisclosure(measure: KpiMeasure): boolean {
  return measure.value === null || measure.records_unmeasured > 0
}

/** The figure, on its own scale, or null when there is nothing to print. */
export function formatValue(measure: KpiMeasure, locale: 'en' | 'ar' = 'en'): string | null {
  if (measure.value === null || !Number.isFinite(measure.value)) return null
  const tag = locale === 'ar' ? 'ar-EG' : 'en-GB'
  const digits = measure.scale === 'money' ? 2 : 1
  const number = measure.value.toLocaleString(tag, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
  if (measure.scale === 'percent') return `${number}%`
  return number
}

/** True when numerator ÷ records reproduces the printed value, which is the
 *  property that lets a reader check a card by hand. A measure that fails it
 *  is not rendered as auditable. */
export function isAuditable(measure: KpiMeasure): boolean {
  if (measure.value === null || measure.records <= 0) return false
  const scale = measure.scale === 'percent' ? 100 : 1
  const expected = (measure.numerator / measure.denominator) * scale
  return Math.abs(expected - measure.value) < Math.max(1e-6, Math.abs(measure.value) * 1e-9)
}
