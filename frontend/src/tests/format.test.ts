import { describe, expect, it } from 'vitest'
import { CURRENCY_CODE, formatMoney } from '../shared/format'

describe('formatMoney', () => {
  it('shows the stated currency by its code, never a symbol two currencies could share', () => {
    expect(formatMoney(1_250_000, 'AED')).toBe('AED 1,250,000.00')
    expect(formatMoney(4332.03, 'USD', 'en')).toBe('USD 4,332.03')
    // Minor units follow the currency: a dinar has three.
    expect(formatMoney(12, 'KWD')).toBe('KWD 12.000')
  })

  it('gives the bare number when no currency is stated, so the caller can say so', () => {
    expect(formatMoney(4332.03, null)).toBe('4,332.03')
    expect(formatMoney(4332.03, undefined)).toBe('4,332.03')
    expect(formatMoney(4332.03, '')).toBe('4,332.03')
    // A malformed code is not a currency either; nothing is assumed from it.
    expect(formatMoney(10, 'dirhams')).toBe('10')
  })

  it('keeps Western digits in Arabic, as every other number does, with the code after the figure', () => {
    expect(formatMoney(1_250_000, 'AED', 'ar')).toBe('‏1,250,000.00 AED')
    expect(formatMoney(4332.03, null, 'ar')).toBe('4,332.03')
  })

  it('accepts the fraction digits a caller asks for', () => {
    expect(formatMoney(1_250_000, 'AED', 'en', { maximumFractionDigits: 0, minimumFractionDigits: 0 })).toBe('AED 1,250,000')
  })

  it('names the ISO 4217 shape the mapping accepts', () => {
    expect(CURRENCY_CODE.test('AED')).toBe(true)
    expect(CURRENCY_CODE.test('aed')).toBe(false)
    expect(CURRENCY_CODE.test('AE')).toBe(false)
  })
})
