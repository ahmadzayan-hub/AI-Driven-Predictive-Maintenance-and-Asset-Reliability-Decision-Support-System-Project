import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApprovalCard } from '../features/runs/ApprovalCard'
import { runFixture } from './run-fixture'
import { applyLocale } from '../i18n'

/** The human gate: Approve needs the exact report opened and read (assessment U3). */
const awaiting = runFixture({
  state: 'awaiting_approval',
  approvals: [{ id: 'approval-test', action: 'publish', target: 'vault', risk: 'high', impact: 'Writes the report', reversibility: 'Reversible', state: 'pending', created_at: '2026-10-16T10:00:00Z', decided_at: null }],
  report: { id: 'report-test', name: 'synthetic report', version: 1, content: '# Synthetic report', published_path: null },
})

describe('approval card', () => {
  afterEach(() => { act(() => applyLocale('en', false)); vi.restoreAllMocks() })

  it('enables Approve only after the exact report was opened and confirmed read', () => {
    const { container } = render(<ApprovalCard detail={awaiting} />)
    const approve = screen.getByRole('button', { name: 'Approve and publish' })
    const read = screen.getByLabelText('I have read this exact report') as HTMLInputElement
    expect(approve).toBeDisabled()
    expect(read).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeEnabled()

    const details = container.querySelector('details') as HTMLDetailsElement
    details.open = true
    fireEvent(details, new Event('toggle'))
    expect(read).toBeEnabled()
    expect(approve).toBeDisabled()

    fireEvent.click(read)
    expect(read.checked).toBe(true)
    expect(approve).toBeEnabled()
  })

  it('keeps the gate in Arabic', () => {
    act(() => applyLocale('ar', false))
    render(<ApprovalCard detail={awaiting} />)
    expect(screen.getByLabelText('قرأت هذا التقرير المحدد')).toBeDisabled()
  })

  it('never offers Approve when the run carries no report', () => {
    render(<ApprovalCard detail={{ ...awaiting, report: null }} />)
    expect(screen.getByRole('button', { name: 'Approve and publish' })).toBeDisabled()
    expect(screen.queryByLabelText('I have read this exact report')).not.toBeNull()
  })
})
