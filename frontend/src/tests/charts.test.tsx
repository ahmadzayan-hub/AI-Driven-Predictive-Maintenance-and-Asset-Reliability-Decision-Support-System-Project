import { render, screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it } from 'vitest'
import { Bars, Figure, Histogram, Line, Scatter } from '../features/dashboard/charts'
import { barGeometry, valueScale } from '../shared/charts'
import dashboardSource from '../features/dashboard/DashboardView.tsx?raw'
import { applyLocale } from '../i18n'

/* The four dashboard conformance rules, pinned where they are decided:
   a value scale that keeps zero, one scale per chart, a mark's colour that
   comes from the datum rather than its position, and a chart that never
   ships without the numbers behind it. Each test is written so that the
   violation it guards against — a truncated baseline, a second axis, an
   index palette, a bare chart — is what makes it fail. */

beforeEach(() => applyLocale('en'))

const fills = (root: HTMLElement) => Array.from(root.querySelectorAll<HTMLElement>('.dash-bars__fill'))
const attr = (node: Element, name: string) => Number(node.getAttribute(name))
/** The drawn marks, not the transparent r="3" circles that only catch a pointer. */
const marks = (root: HTMLElement) =>
  Array.from(root.querySelectorAll('circle')).filter((circle) => attr(circle, 'r') < 2)

describe('axis integrity: the value scale keeps zero', () => {
  it('measures bars from zero, so three close values do not read as nothing to everything', () => {
    const { container } = render(
      <Bars items={[{ label: 'A', value: 100 }, { label: 'B', value: 102 }, { label: 'C', value: 104 }]} label="Total by asset" />,
    )
    const widths = fills(container).map((fill) => Number.parseFloat(fill.style.width))
    // On a scale cut at the smallest value these would be 0, 50 and 100.
    expect(widths[0]).toBeCloseTo((100 / 104) * 100, 5)
    expect(widths[1]).toBeCloseTo((102 / 104) * 100, 5)
    expect(widths[2]).toBeCloseTo(100, 5)
  })

  it('keeps a negative bar visible on the same zero as the positives', () => {
    const { container } = render(<Bars items={[{ label: 'Up', value: 30 }, { label: 'Down', value: -10 }]} label="Change" />)
    const [up, down] = fills(container)
    expect(Number.parseFloat(up.style.width)).toBeCloseTo(75, 5)
    expect(Number.parseFloat(down.style.width)).toBeCloseTo(25, 5)
    expect(down.className).toContain('dash-bars__fill--negative')
    // The two bars meet at one zero: the negative ends where the positive starts.
    expect(Number.parseFloat(down.style.insetInlineStart)).toBeCloseTo(0, 5)
    expect(Number.parseFloat(up.style.insetInlineStart)).toBeCloseTo(25, 5)
  })

  it('draws the distance to zero on a line, not the distance between the readings', () => {
    const { container } = render(<Line points={[{ label: 'Jan', value: 100 }, { label: 'Feb', value: 102 }]} label="Trend" />)
    const axis = container.querySelector('line')!
    expect(attr(axis, 'y1')).toBe(attr(axis, 'y2'))
    const zero = attr(axis, 'y1')
    const [jan, feb] = marks(container).map((circle) => attr(circle, 'cy'))
    expect(zero - jan).toBeCloseTo(40 * (100 / 102), 5)
    expect(jan - feb).toBeCloseTo(40 * (2 / 102), 5)
  })

  it('scales histogram bars by their counts from zero', () => {
    const { container } = render(
      <Histogram bins={[{ from: 0, to: 1, count: 1 }, { from: 1, to: 2, count: 2 }, { from: 2, to: 3, count: 4 }]} label="Distribution" />,
    )
    const heights = Array.from(container.querySelectorAll('rect')).map((rect) => attr(rect, 'height'))
    expect(heights[0] / heights[2]).toBeCloseTo(1 / 4, 5)
    expect(heights[1] / heights[2]).toBeCloseTo(2 / 4, 5)
  })
})

describe('a single value scale per chart', () => {
  /** Axis lines, split by direction: a second scale opposite the first
   *  shows up here as a second line in the same direction. */
  const axes = (root: HTMLElement) => {
    const lines = Array.from(root.querySelectorAll('line'))
    return {
      horizontal: lines.filter((line) => attr(line, 'y1') === attr(line, 'y2')).length,
      vertical: lines.filter((line) => attr(line, 'x1') === attr(line, 'x2')).length,
    }
  }

  it('gives a line one baseline and no second scale', () => {
    const { container } = render(<Line points={[{ label: 'Jan', value: 3 }, { label: 'Feb', value: 5 }]} label="Trend" />)
    expect(axes(container)).toEqual({ horizontal: 1, vertical: 0 })
  })

  it('gives a histogram one baseline', () => {
    const { container } = render(<Histogram bins={[{ from: 0, to: 1, count: 2 }]} label="Distribution" />)
    expect(axes(container)).toEqual({ horizontal: 1, vertical: 0 })
  })

  it('gives a scatter one scale in each direction', () => {
    const { container } = render(<Scatter points={[{ x: 1, y: 2 }, { x: 3, y: 4 }]} label="Relationship" />)
    expect(axes(container)).toEqual({ horizontal: 1, vertical: 1 })
  })
})

describe('colour comes from the datum, never from its position', () => {
  const fillByLabel = (root: HTMLElement) =>
    Object.fromEntries(
      Array.from(root.querySelectorAll('.dash-bars__row')).map((row) => [
        row.querySelector('.dash-bars__label')!.textContent ?? '',
        row.querySelector('.dash-bars__fill')!.className,
      ]),
    )

  it('paints an entity the same way after a filter moves it up the chart', () => {
    // Every entity lands on a different row in the filtered chart, so a
    // palette keyed on the row — however it cycles — reads differently there.
    const all = [{ label: 'North', value: 9 }, { label: 'South', value: -4 }, { label: 'East', value: 2 }]
    const unfiltered = fillByLabel(render(<Bars items={all} label="Total by region" />).container)
    const filtered = fillByLabel(render(<Bars items={all.slice(1)} label="Total by region" />).container)
    expect(Object.keys(filtered)).toEqual(['South', 'East'])
    for (const [label, fill] of Object.entries(filtered)) expect(fill).toBe(unfiltered[label])
    // What the fill does carry is the sign, in both charts.
    expect(filtered.South).toContain('dash-bars__fill--negative')
    expect(filtered.East).not.toContain('dash-bars__fill--negative')
  })

  it('draws every mark of one series in the one series colour', () => {
    const { container } = render(<Scatter points={[{ x: 1, y: 2 }, { x: 3, y: 4 }, { x: 5, y: 6 }]} label="Relationship" />)
    const colours = new Set(marks(container).map((circle) => circle.getAttribute('fill')))
    expect(colours).toEqual(new Set(['var(--accent-solid)']))
  })
})

describe('a table per chart', () => {
  const table = (
    <table>
      <tbody>
        <tr><th scope="row">North</th><td>9</td></tr>
      </tbody>
    </table>
  )

  it('puts the chart and its numbers in one figure, under the title the chart answers to', () => {
    const { container } = render(
      <Figure open title="Total by region" chart={<Bars items={[{ label: 'North', value: 9 }]} label="Total by region" />} table={table} />,
    )
    const figure = within(container.querySelector('figure')!)
    expect(figure.getByRole('img', { name: 'Total by region' })).toBeInTheDocument()
    expect(figure.getByRole('cell', { name: '9' })).toBeInTheDocument()
    expect(screen.getByText('Total by region')).toBeVisible()
  })

  it('keeps the numbers in the page when the table is collapsed', () => {
    const { container } = render(
      <Figure title="Total by region" chart={<Bars items={[{ label: 'North', value: 9 }]} label="Total by region" />} table={table} />,
    )
    expect(container.querySelector('details')!.open).toBe(false)
    expect(container.querySelector('figure')!.textContent).toContain('North')
  })

  it('leaves no chart on the dashboard outside a figure that carries a table', () => {
    const source = dashboardSource
    const charts = Array.from(source.matchAll(/<(Bars|Line|Histogram|Scatter)\b/g))
    expect(charts.length).toBeGreaterThan(0)
    for (const chart of charts) {
      const before = source.slice(0, chart.index).trimEnd()
      expect(before.endsWith('chart={'), `<${chart[1]}> is drawn outside a Figure chart prop`).toBe(true)
    }
    const count = (pattern: RegExp) => (source.match(pattern) ?? []).length
    expect(count(/<Figure\b/g)).toBe(charts.length)
    expect(count(/\btable=\{/g)).toBe(charts.length)
  })
})

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

describe('valueScale: zero is drawn at zero', () => {
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

/** The value labels on the start edge of a chart. */
const scaleLabels = (root: HTMLElement) =>
  Array.from(root.querySelectorAll('text[text-anchor="end"]')).map((node) => node.textContent)

describe('a scale states both of its ends', () => {
  it('labels a line from zero to its maximum', () => {
    const { container } = render(
      <Line label="trend" points={[{ label: 'Jan', value: 120 }, { label: 'Feb', value: 300 }]} />,
    )
    expect(scaleLabels(container)).toEqual(expect.arrayContaining(['300', '0']))
  })

  it('labels a negative minimum on a line', () => {
    const { container } = render(
      <Line label="trend" points={[{ label: 'Jan', value: -10 }, { label: 'Feb', value: 30 }]} />,
    )
    expect(scaleLabels(container)).toContain('-10')
  })

  it('states one label when a line is flat, not two on top of each other', () => {
    const { container } = render(
      <Line label="trend" points={[{ label: 'Jan', value: 0 }, { label: 'Feb', value: 0 }]} />,
    )
    expect(scaleLabels(container).filter((text) => text === '0')).toHaveLength(1)
  })

  it('gives a histogram a count scale from zero', () => {
    const { container } = render(
      <Histogram label="distribution" bins={[{ from: 0, to: 5, count: 3 }, { from: 5, to: 10, count: 12 }]} />,
    )
    expect(scaleLabels(container)).toEqual(expect.arrayContaining(['12', '0']))
  })

  it('labels the lower bound of a scatter plot', () => {
    const { container } = render(<Scatter label="relationship" points={[{ x: 1, y: -4 }, { x: 3, y: 9 }]} />)
    expect(scaleLabels(container)).toEqual(expect.arrayContaining(['9', '-4']))
  })
})
