import { describe, expect, it } from 'vitest'
import { barGeometry, valueScale } from '../shared/charts'

describe('barGeometry', () => {
  it('draws all-positive bars up from a zero line at the bottom', () => {
    const { zero, bars } = barGeometry([10, 5], 4, 50)
    expect(zero).toBe(50)
    expect(bars[0]).toEqual({ y: 4, height: 46, negative: false })
    expect(bars[1].height).toBeCloseTo(23)
  })

  it('draws negative bars down from zero instead of losing them', () => {
    const { zero, bars } = barGeometry([30, -10], 4, 50)
    // 30 of the 40-unit span sits above zero: three quarters of the band.
    expect(zero).toBeCloseTo(4 + 46 * 0.75)
    expect(bars[1].negative).toBe(true)
    expect(bars[1].y).toBeCloseTo(zero)
    expect(bars[1].height).toBeGreaterThan(0)
    expect(bars[1].height).toBeCloseTo(46 * 0.25)
  })

  it('handles all-negative and all-zero values', () => {
    expect(barGeometry([-4, -2], 4, 50).zero).toBe(4)
    const flat = barGeometry([0, 0], 4, 50)
    expect(flat.bars.every((bar) => bar.height === 0)).toBe(true)
  })
})

describe('valueScale', () => {
  it('puts zero at the bottom of the band when every value is positive', () => {
    const scale = valueScale([4, 10], 6, 48)
    expect(scale.min).toBe(0)
    expect(scale.max).toBe(10)
    expect(scale.zero).toBe(48)
    expect(scale.y(10)).toBe(6)
  })

  it('draws zero inside the band, not at its edge, when values cross it', () => {
    const scale = valueScale([-5, 15], 6, 48)
    // 5 of the 20-unit range lies below zero: zero sits a quarter up the band.
    expect(scale.zero).toBeCloseTo(48 - 42 * 0.25)
    expect(scale.y(-5)).toBe(48)
    expect(scale.zero).not.toBe(48)
  })

  it('keeps an all-negative series below a zero line at the top', () => {
    const scale = valueScale([-8, -2], 6, 48)
    expect(scale.max).toBe(0)
    expect(scale.zero).toBe(6)
  })

  it('does not divide by zero for an empty or flat series', () => {
    for (const values of [[], [0, 0]]) {
      const scale = valueScale(values, 6, 48)
      expect(Number.isFinite(scale.zero)).toBe(true)
      expect(scale.min).toBe(scale.max)
    }
  })
})
