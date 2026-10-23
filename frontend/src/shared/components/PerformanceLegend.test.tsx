import { render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import { PerformanceLegend } from './PerformanceValue'

it('keeps performance explanations available in a native collapsed disclosure', () => {
  render(<PerformanceLegend />)
  const summary = screen.getByText('Performance status')
  expect(summary.tagName).toBe('SUMMARY')
  expect(summary.closest('details')).not.toHaveAttribute('open')
  expect(screen.getByText('Not assessed')).toBeInTheDocument()
})
