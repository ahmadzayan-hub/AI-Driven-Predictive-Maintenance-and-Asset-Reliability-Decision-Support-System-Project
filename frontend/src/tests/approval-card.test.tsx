import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApprovalCard } from '../features/runs/ApprovalCard'
import { runFixture } from './run-fixture'
import { applyLocale } from '../i18n'
import { api, ApiError } from '../shared/api'
import { runStore } from '../features/runs/runStore'

/** The human gate: Approve needs the exact report opened and read (assessment U3). */
const awaiting = runFixture({
  state: 'awaiting_approval',
  approvals: [{ id: 'approval-test', action: 'publish', target: 'vault', risk: 'high', impact: 'Writes the report', reversibility: 'Reversible', state: 'pending', created_at: '2026-10-16T10:00:00Z', decided_at: null }],
  report: { id: 'report-test', name: 'synthetic report', version: 1, content: '# Synthetic report', published_path: null },
})

describe('approval card', () => {
  beforeEach(() => { runStore.reset(); vi.spyOn(api, 'getRun').mockResolvedValue(awaiting) })
  afterEach(() => { act(() => { applyLocale('en', false); runStore.reset() }); vi.restoreAllMocks() })

  it('enables Approve only after the exact report was opened and confirmed read', () => {
    const { container } = render(<ApprovalCard detail={awaiting} />)
    const approve = screen.getByRole('button', { name: 'Approve and publish' })
    const read = screen.getByLabelText('I have read this exact report') as HTMLInputElement
    expect(approve).toBeDisabled()
    expect(approve).toHaveAccessibleDescription(/Next: open the exact report/)
    expect(read).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Reject' })).toBeEnabled()

    const details = container.querySelector('details') as HTMLDetailsElement
    details.open = true
    fireEvent(details, new Event('toggle'))
    expect(read).toBeEnabled()
    expect(read).toHaveAccessibleDescription(/Next: confirm that you have read/)
    expect(approve).toBeDisabled()

    fireEvent.click(read)
    expect(read.checked).toBe(true)
    expect(approve).toBeEnabled()
    expect(approve).toHaveAccessibleDescription(/Nothing is published until/)
    fireEvent.click(read)
    expect(approve).toBeDisabled()
    expect(approve).toHaveAccessibleDescription(/Next: confirm that you have read/)
  })

  it('keeps the gate in Arabic', () => {
    act(() => applyLocale('ar', false))
    render(<ApprovalCard detail={awaiting} />)
    expect(screen.getByLabelText('قرأت هذا التقرير المحدد')).toBeDisabled()
    expect(screen.getByLabelText('قرأت هذا التقرير المحدد')).toHaveAccessibleDescription(/افتح التقرير المحدد/)
  })

  it('never offers Approve when the run carries no report', () => {
    vi.mocked(api.getRun).mockResolvedValue({ ...awaiting, report: null })
    render(<ApprovalCard detail={{ ...awaiting, report: null }} />)
    expect(screen.getByRole('button', { name: 'Approve and publish' })).toBeDisabled()
    expect(screen.queryByLabelText('I have read this exact report')).not.toBeNull()
  })

  it('requires a new report read when another tab replaces the pending review', async () => {
    const { container } = render(<ApprovalCard detail={awaiting} />)
    await act(async () => {})
    const details = container.querySelector('details')!
    details.open = true; fireEvent(details, new Event('toggle'))
    fireEvent.click(screen.getByLabelText('I have read this exact report'))
    expect(screen.getByRole('button', { name: 'Approve and publish' })).toBeEnabled()
    act(() => runStore.receive({ ...awaiting, approvals: [{ ...awaiting.approvals[0], id: 'new-review', target: 'database:Reports' }] }))
    expect(screen.getByLabelText('I have read this exact report')).not.toBeChecked()
    expect(screen.getByLabelText('I have read this exact report')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Approve and publish' })).toBeDisabled()
    expect(container.querySelector('details')).not.toHaveAttribute('open')
  })

  it('resets guidance and consent when the same approval points to a new report version', async () => {
    const { container } = render(<ApprovalCard detail={awaiting} />)
    await act(async () => {})
    const details = container.querySelector('details')!
    details.open = true; fireEvent(details, new Event('toggle'))
    fireEvent.click(screen.getByLabelText('I have read this exact report'))
    act(() => runStore.receive({ ...awaiting, report: { ...awaiting.report!, version: 2 } }))
    const approve = screen.getByRole('button', { name: 'Approve and publish' })
    expect(approve).toBeDisabled()
    expect(approve).toHaveAccessibleDescription(/Next: open the exact report/)
    expect(screen.getByLabelText('I have read this exact report')).not.toBeChecked()
  })

  it('refreshes a changed destination without publishing or carrying old consent', async () => {
    const changed = new ApiError('Synthetic changed destination', 409)
    changed.code = 'publication_destination_changed'
    vi.spyOn(api, 'decideApproval').mockRejectedValue(changed)
    vi.spyOn(api, 'refreshPublicationReview').mockResolvedValue({ ...awaiting,
      approvals: [{ ...awaiting.approvals[0], id: 'review-new', target: 'database:Reports' }],
    })
    const { container } = render(<ApprovalCard detail={awaiting} />)
    await act(async () => {})
    const details = container.querySelector('details')!
    details.open = true; fireEvent(details, new Event('toggle'))
    fireEvent.click(screen.getByLabelText('I have read this exact report'))
    fireEvent.click(screen.getByRole('button', { name: 'Approve and publish' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Update destination for a new review' }))
    await waitFor(() => expect(screen.getByText('database:Reports')).toBeVisible())
    expect(api.decideApproval).toHaveBeenCalledOnce()
    expect(api.refreshPublicationReview).toHaveBeenCalledOnce()
    expect(screen.getByLabelText('I have read this exact report')).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Approve and publish' })).toBeDisabled()
    expect(runStore.get(awaiting.id).detail?.report?.published_path).toBeNull()
  })
})
