import { describe, expect, it } from 'vitest'
import { formatNumberIn } from '../i18n'
import { faithfulOptions } from './faithfulNumber'

const say = (value: number, locale: 'en' | 'ar' = 'en') => formatNumberIn(locale, value, faithfulOptions(value))

describe('faithfulOptions', () => {
  it('keeps two decimals where rounding changes nothing a reader would act on', () => {
    expect(say(1517510.2300000011)).toBe('1,517,510.23')
    expect(say(42.123)).toBe('42.12')
    expect(say(100)).toBe('100')
    expect(say(0)).toBe('0')
  })
  it('never reads a value just under 100 as 100', () => {
    expect(say(99.996)).toBe('99.996')
    expect(say(99.9999)).toBe('99.9999')
  })
  it('never reads a small value as zero', () => {
    expect(say(0.004)).toBe('0.004')
    expect(say(-0.0004)).toBe('-0.0004')
    expect(say(0.00000012)).toBe('0.00000012')
  })
  it('applies the same digits in Arabic', () => {
    expect(say(99.996, 'ar')).toBe(formatNumberIn('ar', 99.996, { maximumFractionDigits: 3 }))
  })
})
