import { render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import type { RunDetail, RunTask } from '../../shared/types'
import { RunTimeline } from './RunTimeline'

beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
})

// The pipeline names the stage running now and marks it (ADR 2026-10-28-live-pipeline).
function task(id: string, title: string, state: string): RunTask {
  return { id, role: id, title, state, summary: null, quality_checks: [], claims: [] }
}

function runWith(tasks: RunTask[]): RunDetail {
  return { id: 'r1', report_language: 'en', tasks } as unknown as RunDetail
}

it.each(['en', 'ar'] as const)('names the stage running now and marks it as the current step (%s)', (locale) => {
  applyLocale(locale)
  const run = runWith([task('a', 'Collect data', 'succeeded'), task('b', 'Model the trend', 'running'), task('c', 'Report', 'pending')])
  render(<RunTimeline run={run} pipelines={null} onEvidence={() => {}} />)
  expect(screen.getByText(locale === 'ar' ? 'الآن: Model the trend' : 'Now: Model the trend')).toBeVisible()
  const current = document.querySelector('.runtask--current')
  expect(current).toHaveAttribute('aria-current', 'step')
  expect(current).toHaveTextContent('Model the trend')
  expect(screen.getByRole('status')).toBeInTheDocument()
})
