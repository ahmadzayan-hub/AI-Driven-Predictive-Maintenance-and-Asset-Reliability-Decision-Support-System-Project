import { render } from '@testing-library/react'
import { beforeEach, expect, it } from 'vitest'
import { applyLocale } from '../../i18n'
import { Histogram, Line, Scatter } from './charts'

beforeEach(() => applyLocale('en'))

function axisLabels(container: HTMLElement) {
  return Array.from(container.querySelectorAll('text[text-anchor="end"]')).map((node) => node.textContent)
}

it('labels both ends of a line chart scale, including zero', () => {
  const { container } = render(
    <Line label="trend" points={[{ label: 'Jan', value: 120 }, { label: 'Feb', value: 300 }]} />,
  )
  const labels = axisLabels(container)
  expect(labels).toContain('300')
  expect(labels).toContain('0')
})

it('draws the zero line of a line chart where zero falls, not at the bottom', () => {
  const { container } = render(
    <Line label="trend" points={[{ label: 'Jan', value: -10 }, { label: 'Feb', value: 30 }]} />,
  )
  const zero = container.querySelector('line')
  // The band runs from 6 to 46 and a quarter of the range is below zero.
  expect(Number(zero?.getAttribute('y1'))).toBeCloseTo(46 - 40 * 0.25)
  expect(axisLabels(container)).toContain('-10')
})

it('states one label when a line is flat, not two on top of each other', () => {
  const { container } = render(
    <Line label="trend" points={[{ label: 'Jan', value: 0 }, { label: 'Feb', value: 0 }]} />,
  )
  expect(axisLabels(container).filter((text) => text === '0')).toHaveLength(1)
})

it('gives a histogram a count scale from zero', () => {
  const { container } = render(
    <Histogram label="distribution" bins={[{ from: 0, to: 5, count: 3 }, { from: 5, to: 10, count: 12 }]} />,
  )
  const labels = axisLabels(container)
  expect(labels).toContain('12')
  expect(labels).toContain('0')
})

it('labels the lower bound of a scatter plot', () => {
  const { container } = render(
    <Scatter label="relationship" points={[{ x: 1, y: -4 }, { x: 3, y: 9 }]} />,
  )
  const labels = axisLabels(container)
  expect(labels).toContain('9')
  expect(labels).toContain('-4')
})
