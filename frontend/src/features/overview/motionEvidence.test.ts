import { describe, expect, it } from 'vitest'
import type { RunDetail, RunTask } from '../../shared/types'
import { motionFromRun } from './motionEvidence'

const task = (role: string, state: string, checks: boolean[] = []): RunTask => ({
  id: role, role, title: role, state, summary: null,
  quality_checks: checks.map((passed, n) => ({ name: String(n), passed, detail: 'fixture' })),
  claims: [],
})

function fixture(): RunDetail {
  return {
    id: 'run-42', goal: 'Assess asset downtime', dataset_name: 'test-data',
    report_language: 'en', report: { id: 'report-1', version: 2, name: 'Draft report',
      content: 'Source-backed example', published_path: null },
    reports: [{ type: 'descriptive', title: 'Finding', question: 'What happened?',
      headline: 'Downtime was measured on the synthetic fixture', content: 'Evidence' }],
    tasks: [task('planner', 'succeeded'), task('validator', 'succeeded', [true])],
  } as RunDetail
}

describe('source-backed motion drafts', () => {
  it('retains the exact run/report identifiers and draft-only state', () => {
    const draft = motionFromRun(fixture())
    expect(draft.source_context.run_id).toBe('run-42')
    expect(draft.scenes[1].text).toContain('Downtime was measured')
    expect(draft.scenes[1].evidence[0]).toMatchObject({
      source_id: 'run-42', revision: 'v2', locator: 'report:report-1',
    })
    expect(draft.approval.issued).toBe(false)
  })
  it('refuses run without a completed validator', () => {
    const run = fixture()
    run.tasks[1].quality_checks = []
    expect(() => motionFromRun(run)).toThrow()
  })
  it('refuses to invent narrative if the report is missing', () => {
    const run = fixture()
    run.report = null
    expect(() => motionFromRun(run)).toThrow()
  })
})
