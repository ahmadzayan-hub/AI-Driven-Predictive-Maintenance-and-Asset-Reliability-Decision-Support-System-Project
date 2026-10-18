import { describe, expect, it } from 'vitest'
import type { RunTask } from '../../shared/types'
import { summarizeRunEvidence } from './evidence'

function task(role: string, state: string, checks: boolean[] = []): RunTask {
  return {
    id: role, role, title: role, state, summary: null,
    quality_checks: checks.map((passed, i) => ({
      name: `check_${i}`, passed, detail: 'Synthetic test check',
    })),
    claims: [],
  }
}

describe('run evidence status', () => {
  it('shows unavailable when no run has been inspected', () => {
    expect(summarizeRunEvidence(null).status).toBe('unavailable')
  })
  it('fails closed for older responses with no task array', () => {
    const incomplete = {} as Pick<import('../../shared/types').RunDetail, 'tasks'>
    expect(summarizeRunEvidence(incomplete)).toEqual({ status: 'pending', completed: 0, total: 0 })
  })
  it('does not claim success without independent validator evidence', () => {
    expect(summarizeRunEvidence({ tasks: [task('planner', 'succeeded')] }).status).toBe('pending')
    expect(summarizeRunEvidence({ tasks: [task('validator', 'succeeded')] }).status).toBe('pending')
  })
  it('does not claim success if a stage or validator check fails', () => {
    expect(summarizeRunEvidence({ tasks: [
      task('planner', 'failed'), task('validator', 'succeeded', [true]),
    ] }).status).toBe('pending')
    expect(summarizeRunEvidence({ tasks: [
      task('planner', 'succeeded'), task('validator', 'succeeded', [false]),
    ] }).status).toBe('pending')
  })
  it('counts stage completion but never counts the publication action', () => {
    const status = summarizeRunEvidence({ tasks: [
      task('planner', 'succeeded'),
      task('validator', 'succeeded', [true, true]),
      task('publish', 'awaiting_approval'),
    ] })
    expect(status).toEqual({ status: 'passed', completed: 2, total: 2 })
  })
})
