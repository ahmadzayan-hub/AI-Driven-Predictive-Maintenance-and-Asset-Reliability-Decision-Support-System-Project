import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { NextAction, nextActionRun } from './NextAction'
import { summarizeRunEvidence } from './evidence'
import { countRuns } from './summary'
import type { RunState, RunSummary, RunTask } from '../../shared/types'

const run = (state: RunState, id = state): RunSummary => ({ id, state, goal: 'Synthetic review', dataset_name: 'Synthetic fleet', created_at: '2026-10-23T09:00:00Z', updated_at: '2026-10-23T09:00:00Z' })
function renderAction(runs: RunSummary[], canStart = true) {
  const onUpload = vi.fn(), onOpenRun = vi.fn()
  render(<NextAction runs={runs} canStart={canStart} onUpload={onUpload} onOpenRun={onOpenRun} />)
  return { onUpload, onOpenRun }
}

describe('task-first journey', () => {
  it('starts from the upload path without pretending quality was checked', () => {
    const { onUpload } = renderAction([])
    expect(screen.getByText('Prepare your data').closest('li')).toHaveAttribute('aria-current', 'step')
    expect(screen.getByText('Check quality').closest('li')).not.toHaveAttribute('aria-current')
    fireEvent.click(screen.getByRole('button', { name: 'Upload data' }))
    expect(onUpload).toHaveBeenCalledOnce()
  })
  it('24 successful stages can coexist with a report awaiting approval, never published', () => {
    const waiting = run('awaiting_approval')
    const tasks = Array.from({ length: 24 }, (_, n) => ({ id: String(n), role: n === 23 ? 'validator' : `stage${n}`, title: 'Synthetic', state: 'succeeded', summary: null, claims: [], quality_checks: [{ name: 'fixture', detail: 'Synthetic', passed: true }] })) as RunTask[]
    expect(summarizeRunEvidence({ tasks })).toEqual({ status: 'passed', completed: 24, total: 24 })
    expect(countRuns([waiting]).finished).toBe(0)
    const { onOpenRun } = renderAction([waiting])
    expect(screen.getByRole('heading', { name: 'Report available · awaiting your review' })).toBeInTheDocument()
    const guidance = screen.getByText(/Analysis progress is not approval/)
    expect(guidance).not.toBeVisible()
    fireEvent.click(screen.getByText('Workflow steps'))
    expect(guidance).toBeVisible()
    fireEvent.click(screen.getByRole('button', { name: 'Review this report' }))
    expect(onOpenRun).toHaveBeenCalledWith(waiting.id)
  })
  it.each(['queued', 'running'] as RunState[])('shows observed active state %s', (state) => {
    renderAction([run(state)])
    expect(screen.getByRole('heading', { name: 'Your analysis is in progress' })).toBeInTheDocument()
    expect(screen.getByText('Run analysis').closest('li')).toHaveAttribute('aria-current', 'step')
  })
  it.each(['failed', 'partially_completed'] as RunState[])('does not turn %s into success', (state) => {
    renderAction([run(state)])
    expect(screen.getByRole('heading', { name: 'This analysis needs attention' })).toBeInTheDocument()
  })
  it('does not ask for approval again on a completed run', () => {
    expect(nextActionRun([run('completed')])).toBeUndefined()
  })
  it('prioritizes review over active work and preserves the exact run id', () => {
    expect(nextActionRun([run('running'), run('awaiting_approval')])?.id).toBe('awaiting_approval')
  })
  it('keeps demo read-only, even when a sample is awaiting approval', () => {
    const { onUpload, onOpenRun } = renderAction([run('awaiting_approval')], false)
    expect(screen.queryByRole('button', { name: 'Review this report' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Upload data' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Open analysis' }))
    expect(onUpload).not.toHaveBeenCalled()
    expect(onOpenRun).toHaveBeenCalledWith('awaiting_approval')
  })
})
