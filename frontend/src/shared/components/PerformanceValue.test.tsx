import { act, cleanup, render, screen } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'
import { applyLocale } from '../../i18n'
import { PerformanceLegend, PerformanceValue, performanceTone, type PerformanceTone } from './PerformanceValue'
import { performanceMessages } from './performanceMessages'

const tokensCss = readFileSync(resolve('src/shared/styles/tokens.css'), 'utf8')
const performanceCss = readFileSync(resolve('src/shared/components/performance.css'), 'utf8')

afterEach(() => { cleanup(); act(() => applyLocale('en')) })

describe('explicit performance assessments', () => {
  it.each(['en', 'ar'] as const)('explains every color and both neutral meanings in %s without a tooltip', (locale) => {
    applyLocale(locale)
    render(<PerformanceLegend />)
    expect(screen.getByRole('complementary', { name: performanceMessages[locale]['performance.legend'] })).toBeVisible()
    for (const tone of ['bad', 'okay', 'good', 'unassessed', 'unavailable'] as const) {
      expect(screen.getByText(performanceMessages[locale][`performance.${tone}`])).toBeVisible()
    }
    expect(screen.getByText(performanceMessages[locale]['performance.explanation'])).toBeVisible()
  })

  it('never treats a number, percentage or sign as a target assessment', () => {
    for (const value of [-100, -1, 0, 50, 100, 10_000]) {
      expect(performanceTone(value)).toBe('unassessed')
      expect(performanceTone(value, { status: 'unknown' })).toBe('unassessed')
    }
  })

  it('keeps absent and non-finite readings unavailable even with a supplied good assessment', () => {
    for (const value of [null, undefined, NaN, Infinity, -Infinity]) {
      expect(performanceTone(value, { status: 'good' })).toBe('unavailable')
    }
  })

  it.each(['good', 'okay', 'bad', 'unassessed', 'unavailable'] as const)('renders the explicit %s state with visible words and the unchanged value', (tone) => {
    const { container } = render(<PerformanceValue tone={performanceTone(57.5, { status: tone })}><bdi>57.5 %</bdi></PerformanceValue>)
    expect(container.querySelector('[data-performance]')).toHaveAttribute('data-performance', tone)
    expect(screen.getByText('57.5 %')).toBeVisible()
    expect(screen.getByText(performanceMessages.en[`performance.${tone}`])).toBeVisible()
  })

  it('uses Arabic labels while preserving formatted children, source reasons and an explicit status label', () => {
    applyLocale('ar')
    const { rerender } = render(<PerformanceValue tone="okay" reason="ضمن النطاق المعتمد"><bdi>٥٧٫٥ ٪</bdi></PerformanceValue>)
    expect(screen.getByText('مقبول')).toBeVisible()
    expect(screen.getByText('٥٧٫٥ ٪')).toBeVisible()
    expect(screen.getByText('ضمن النطاق المعتمد')).toHaveAttribute('dir', 'auto')
    rerender(<PerformanceValue tone="okay" status="قيد المتابعة"><bdi>٥٧٫٥ ٪</bdi></PerformanceValue>)
    expect(screen.getByText('قيد المتابعة')).toBeVisible()
    expect(screen.queryByText('مقبول')).not.toBeInTheDocument()
    expect(Object.keys(performanceMessages.ar)).toEqual(Object.keys(performanceMessages.en))
  })
})

function colors(source: string) {
  return Object.fromEntries([...source.matchAll(/--([\w-]+):\s*(#[\da-f]{6})/gi)].map((match) => [match[1], match[2]]))
}
function luminance(hex: string) {
  return [.2126, .7152, .0722].reduce((sum, weight, index) => {
    const channel = parseInt(hex.slice(index * 2 + 1, index * 2 + 3), 16) / 255
    return sum + weight * (channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4)
  }, 0)
}
function contrast(a: string, b: string) {
  const [lo, hi] = [luminance(a), luminance(b)].sort((x, y) => x - y)
  return (hi + .05) / (lo + .05)
}
function foreground(tone: PerformanceTone, theme: Record<string, string>) {
  const block = performanceCss.match(new RegExp(`\\.performance-value\\[data-performance='${tone}'\\]\\s*\\{([^}]+)`))?.[1]
    ?? performanceCss.match(/\.performance-value\s*\{([^}]+)/)![1]
  const variable = block.match(/color:\s*var\(--([\w-]+)\)/)![1]
  return theme[variable]
}

describe('actual semantic source colors', () => {
  const light = colors(tokensCss.split("[data-theme='dark']")[0])
  const dark = { ...light, ...colors(tokensCss.split("[data-theme='dark']")[1].split('@media')[0]) }
  const systemDark = { ...light, ...colors(tokensCss.split('@media (prefers-color-scheme: dark)')[1]) }
  it.each([['light', light], ['dark', dark], ['system dark', systemDark]] as const)('keeps small metric text readable on %s card surfaces', (_name, theme) => {
    for (const tone of ['good', 'okay', 'bad', 'unassessed', 'unavailable'] as const) {
      for (const background of ['surface', 'surface-raised', 'surface-sunken']) {
        expect(contrast(foreground(tone, theme), theme[background]), `${tone} on ${background}`).toBeGreaterThanOrEqual(4.5)
      }
    }
    const red = foreground('bad', theme)
    const blue = foreground('okay', theme)
    const green = foreground('good', theme)
    const channel = (hex: string, index: number) => parseInt(hex.slice(index * 2 + 1, index * 2 + 3), 16)
    expect(channel(red, 0)).toBeGreaterThan(Math.max(channel(red, 1), channel(red, 2)))
    expect(channel(blue, 2)).toBeGreaterThan(Math.max(channel(blue, 0), channel(blue, 1)))
    expect(channel(green, 1)).toBeGreaterThan(Math.max(channel(green, 0), channel(green, 2)))
  })

  it('keeps system-dark metric semantics identical to explicit dark mode', () => {
    for (const tone of ['good', 'okay', 'bad', 'unassessed', 'unavailable'] as const) {
      expect(foreground(tone, systemDark)).toBe(foreground(tone, dark))
    }
  })
})
