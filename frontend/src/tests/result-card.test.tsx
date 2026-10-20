import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MessageBubble } from '../features/chat/MessageBubble'
import { cardType } from '../features/chat/ResultCard'
import type { TranscriptEntry } from '../shared/types'
import AgentCollaboration from '../features/runs/AgentCollaboration'
import { runFixture } from './run-fixture'
import { appendEvents, snapshotEvents } from '../features/runs/runEvents'
import { applyLocale } from '../i18n'

const entry: TranscriptEntry = { id: 1, role: 'agent', text: '<img src=x onerror=alert(1)>', time: '2026-10-16T10:00:00Z', action: 'unknown-card' }
describe('typed assistant results', () => {
  it('falls back to ordinary text for an unknown action', () => {
    expect(cardType(entry)).toBeNull()
    const { container } = render(<MessageBubble entry={entry} agentName="Test Agent" />)
    expect(screen.getByText(entry.text)).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('.result-card')).toBeNull()
  })
  it('only creates a run card for a known action and a returned identifier', () => {
    expect(cardType({ ...entry, action: 'start_run' })).toBeNull()
    expect(cardType({ ...entry, action: 'start_run', result: { run_id: 'run-test' } })).toBe('run')
    expect(cardType({ ...entry, action: 'explain_report', result: { run_id: 'run-test' } })).toBe('run')
    expect(cardType({ ...entry, action: 'runtime', result: { run_id: 'run-test' } })).toBe('run')
    expect(cardType({ ...entry, role: 'user', action: 'start_run', result: { run_id: 'run-test' } })).toBeNull()
  })
})

describe('interactive agent observations', () => {
  afterEach(() => { act(() => applyLocale('en', false)); vi.restoreAllMocks() })
  const task = runFixture().tasks[0]
  const before = runFixture({ state: 'running', tasks: [{ ...task, state: 'running', summary: 'First result', quality_checks: [{ name: 'test', passed: true, detail: 'Recorded check' }] }] })
  const after = runFixture({ state: 'completed', updated_at: '2026-10-16T10:01:00Z', tasks: [{ ...before.tasks[0], state: 'succeeded', summary: 'New result' }] })
  const events = snapshotEvents(null, before)
  const later = appendEvents(events, snapshotEvents(before, after))
  it('holds the view while updates continue, opens current evidence, then resumes', () => {
    const evidence = vi.fn()
    const props = { pipelines: null, interrupted: false, onEvidence: evidence }
    const { rerender, container } = render(<AgentCollaboration key={before.id} {...props} run={before} events={events} />)
    fireEvent.click(screen.getByRole('button', { name: /^Analytics/ }))
    fireEvent.click(screen.getByRole('button', { name: 'Pause live view' }))
    rerender(<AgentCollaboration key={after.id} {...props} run={after} events={later} />)
    expect(screen.getByText('First result')).toBeVisible()
    expect(screen.queryByText('New result')).toBeNull()
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-still', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Open current evidence' }))
    expect(evidence).toHaveBeenCalledWith(after.tasks[0])
    fireEvent.click(screen.getByRole('button', { name: 'Resume live view' }))
    expect(screen.getByText('New result')).toBeVisible()
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-working', 'false')
    // A new run unmounts the held snapshot; an old run's results cannot leak.
    fireEvent.click(screen.getByRole('button', { name: 'Pause live view' }))
    rerender(<AgentCollaboration key="other-run" {...props} run={runFixture({ id: 'other-run' })} events={later} />)
    expect(screen.queryByText('New result')).toBeNull()
    expect(screen.getByRole('button', { name: 'Pause live view' })).toHaveAttribute('aria-pressed', 'false')
    expect(container.querySelector('.agent-flow__latest')).toBeNull()
  })
  it('selects a configured custom stage, escapes returned content and exposes workflow order', () => {
    const custom = { ...task, id: 'custom', role: 'target', title: '<img src=x onerror=alert(1)>', summary: '<script>bad()</script>' }
    const run = runFixture({ tasks: [task, custom, { ...task, id: 'publish', role: 'publish', title: 'Publish report' }] })
    const pipelines = { stages: [{ role: 'target', title: 'Target', after: 'descriptive', question: null, can_fail_run: false }], profiles: {}, default: [], problems: [] }
    const { container } = render(<AgentCollaboration run={run} events={[]} interrupted={false} pipelines={pipelines} onEvidence={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /^Analytics/ }))
    fireEvent.click(screen.getByRole('button', { name: /<img/ }))
    expect(screen.getByText(custom.summary)).toBeVisible()
    expect(container.querySelector('img, script')).toBeNull()
    expect(within(container.querySelector('.agent-flow__handoff')! as HTMLElement).getByText('Publish report')).toBeVisible()
    expect(screen.getByText(/Connections show stage order/)).toBeVisible()
  })
  it('suspends visual motion on disconnection and when the document is hidden', () => {
    const props = { run: before, events, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} interrupted={true} />)
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-still', 'true')
    expect(screen.getByText(/Connection interrupted/)).toBeVisible()
    rerender(<AgentCollaboration {...props} interrupted={false} />)
    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    fireEvent(document, new Event('visibilitychange'))
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-still', 'true')
  })
  it('shows bounded activity and translated approval decisions in Arabic', () => {
    applyLocale('ar', false)
    const run = runFixture({ state: 'completed', tasks: [{ ...task, state: 'succeeded' }] })
    const base = snapshotEvents(null, run)[0]
    const observations = Array.from({ length: 20 }, (_, i) => ({ ...base, id: String(i), kind: 'approval.decided' as const, state: i % 2 ? 'approved' : 'rejected' }))
    const { container } = render(<AgentCollaboration run={run} events={observations} interrupted={false} pipelines={null} onEvidence={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /^التحليلات/ }))
    fireEvent.click(screen.getByText('النشاط المرصود'))
    expect(container.querySelectorAll('.agent-flow__activity li')).toHaveLength(12)
    expect(screen.getByText('عرض أحدث 12 من أصل 20 مشاهدة محفوظة')).toBeVisible()
    expect(screen.getAllByText('المراجعة البشرية: تمت الموافقة')[0]).toBeVisible()
    expect(screen.getAllByText('المراجعة البشرية: رُفضت')[0]).toBeVisible()
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__group bdi')).toHaveAttribute('dir', 'ltr')
    expect(screen.getByText('بداية سير العمل')).not.toHaveAttribute('lang')
    expect(screen.getByText('نهاية سير العمل')).not.toHaveAttribute('lang')
  })
})
