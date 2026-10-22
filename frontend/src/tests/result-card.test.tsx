import { act, fireEvent, render, screen, within } from '@testing-library/react'
import { createRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { MessageBubble } from '../features/chat/MessageBubble'
import { cardType } from '../features/chat/ResultCard'
import type { TranscriptEntry } from '../shared/types'
import AgentCollaboration from '../features/runs/AgentCollaboration'
import { runFixture } from './run-fixture'
import { appendEvents, snapshotEvents } from '../features/runs/runEvents'
import { applyLocale } from '../i18n'
import { ReportDocument } from '../features/runs/ReportDocument'

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

describe('safe report documents', () => {
  it('keeps repeated unmatched markup literal without reparsing each remaining suffix', () => {
    const blocks = ['[', '<', '[', '<'].map((char) => `Text ${char.repeat(15_900)} END 001.250`)
    const content = blocks.join('\n\n') + '\n\n[literal **label**](https://example.test)'
    const { container } = render(<ReportDocument content={content} language="en" label="Malformed report" />)
    for (const block of blocks) expect(container.textContent).toContain(block)
    expect(container.textContent).toContain('[literal **label**](https://example.test)')
    expect(container.querySelector('a, strong')).toBeNull()
  })
  it('renders the generated report structure with semantic headings, emphasis, lists and quotations', () => {
    const content = [
      '# Maintenance report', '## Findings', '',
      'The **confirmed result** includes *reviewed evidence* and `pump_A-01`.', '',
      '- Inspect the seal', '- Retain evidence', '',
      '3. First recorded action', '7. Seventh recorded action', '',
      '> Human review is required.', '> Evidence remains attached.', '', '---',
    ].join('\n')
    const { container } = render(<ReportDocument content={content} language="en" label="Published report" />)
    expect(screen.getByRole('heading', { level: 2, name: 'Maintenance report' })).toBeVisible()
    expect(screen.getByRole('heading', { level: 3, name: 'Findings' })).toBeVisible()
    expect(container.querySelector('strong')).toHaveTextContent('confirmed result')
    expect(container.querySelector('em')).toHaveTextContent('reviewed evidence')
    expect(container.querySelector('code')).toHaveTextContent('pump_A-01')
    expect(container.querySelectorAll('ul li')).toHaveLength(2)
    expect(container.querySelector('ol')).toHaveAttribute('start', '3')
    expect(container.querySelectorAll('ol li')[1]).toHaveAttribute('value', '7')
    expect(container.querySelector('blockquote')).toHaveTextContent('Human review is required.')
    expect(container.querySelector('blockquote')).toHaveTextContent('Evidence remains attached.')
    expect(screen.getByRole('separator')).toBeInTheDocument()
  })

  it('renders Arabic tables with exact values, empty cells, escaped pipes and explicit numeric isolation', () => {
    const content = [
      '# تقرير الصيانة', '## المؤشرات', '',
      '| الأصل | القيمة | الملاحظة |', '| :--- | ---: | :---: |',
      '| مضخة A-01 | -0.0001250% | |',
      '| محرك B-02 | 9007199254740993.125 | ضغط \\| تدفق |',
      '| احتياطي | ٠٫٠٠٥٠ | 0 |',
    ].join('\n')
    const { container } = render(<ReportDocument content={content} language="ar" label="التقرير المنشور" />)
    const region = screen.getByRole('region', { name: 'التقرير المنشور' })
    expect(region).toHaveAttribute('lang', 'ar')
    expect(region).toHaveAttribute('dir', 'rtl')
    expect(region).toHaveAttribute('tabindex', '0')
    const table = screen.getByRole('table', { name: 'المؤشرات' })
    expect(table.parentElement).toHaveAttribute('tabindex', '0')
    const headers = within(table).getAllByRole('columnheader')
    expect(headers.map((cell) => cell.style.textAlign)).toEqual(['left', 'right', 'center'])
    expect(headers.every((cell) => cell.getAttribute('scope') === 'col')).toBe(true)
    const rows = within(table).getAllByRole('row').slice(1)
    expect(within(rows[0]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['مضخة A-01', '-0.0001250%', ''])
    expect(within(rows[1]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['محرك B-02', '9007199254740993.125', 'ضغط | تدفق'])
    expect(within(rows[2]).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['احتياطي', '٠٫٠٠٥٠', '0'])
    expect(within(rows[0]).getAllByRole('cell')[1].querySelector('bdi')).toHaveAttribute('dir', 'ltr')
    expect(container.querySelector('h1')).toBeNull()
  })

  it('keeps HTML, links, images and fenced executable-looking code inert and readable', () => {
    const attack = '<script>alert("report")</script> <img src=x onerror=alert(1)>'
    const links = '[Open](javascript:alert(1)) ![Image](https://example.test/tracker.png) <https://example.test>'
    const code = '<iframe src="https://example.test"></iframe>\n  const exact = "001.2300";\n'
    const content = `${attack}\n\n${links}\n\n\`\`\`html\n${code}\`\`\``
    const { container } = render(<ReportDocument content={content} language="en" label="Untrusted report" />)
    expect(container.querySelector('script, img, iframe, a, object, embed, style')).toBeNull()
    expect(container.textContent).toContain(attack)
    expect(container.textContent).toContain(links)
    expect(container.querySelector('pre code')?.textContent).toBe(code)
    expect(container.querySelector('pre')).toHaveAttribute('dir', 'ltr')
    expect(container.querySelector('pre')).toHaveAttribute('tabindex', '0')
  })

  it('preserves pipe-containing code and malformed extra cells instead of dropping report values', () => {
    const content = ['Name | Value', '--- | ---', '`A|B` | 1.230000', 'extra | 2 | MUST KEEP', '', '**unclosed', '', '~~~text', 'literal **not bold** | 00042'].join('\n')
    const { container } = render(<ReportDocument content={content} language="en" label="Report evidence" />)
    const table = screen.getByRole('table', { name: 'Report evidence' })
    expect(within(table).getAllByRole('cell').map((cell) => cell.textContent)).toEqual(['A|B', '1.230000'])
    expect(container.textContent).toContain('extra | 2 | MUST KEEP')
    expect(container.textContent).toContain('**unclosed')
    expect(container.querySelector('pre code')?.textContent).toBe('literal **not bold** | 00042')
    expect(container.querySelector('pre strong')).toBeNull()
  })

  it('forwards its React19 ref and preserves oversized and over-line-limit content as literal text', () => {
    const ref = createRef<HTMLDivElement>()
    const content = `${'x'.repeat(200_001)}\nFINAL 9007199254740993.000`
    const { rerender, container } = render(<ReportDocument ref={ref} content={content} language="en" label="Long report" className="preview" />)
    expect(ref.current).toBe(screen.getByRole('region', { name: 'Long report' }))
    expect(ref.current).toHaveClass('runreport', 'report-document', 'preview')
    expect(ref.current).toHaveAttribute('dir', 'ltr')
    expect(container.querySelector('.report-document__literal')?.textContent).toBe(content)
    const lines = Array.from({ length: 4_005 }, (_, index) => `Value ${index}.000`).join('\n')
    rerender(<ReportDocument content={lines} language="en" label="Long report" />)
    expect(container.textContent).toContain('Value 3999.000')
    expect(container.querySelector('.report-document__literal')?.textContent).toBe(lines.split('\n').slice(4_000).join('\n'))
    expect(container.textContent).toContain('Value 4004.000')
  })
})

describe('interactive agent observations', () => {
  afterEach(() => {
    act(() => applyLocale('en', false))
    vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.useRealTimers()
    delete document.documentElement.dataset.motion
  })
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
    // This update arrived while held and has not previously been observed.
    expect(container.querySelector('.agent-flow__signal--updated')).toHaveAttribute('data-direction', 'inbound')
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
  it('bounds workspace zoom and fits the graph without changing the selected stage or run', () => {
    const evidence = vi.fn()
    const { container } = render(<AgentCollaboration run={before} events={events} interrupted={false} pipelines={null} onEvidence={evidence} />)
    const canvas = container.querySelector('.agent-flow__canvas')!
    const viewport = container.querySelector('.agent-flow__viewport')!
    const zoomIn = screen.getByRole('button', { name: 'Zoom in' })
    const zoomOut = screen.getByRole('button', { name: 'Zoom out' })
    for (let i = 0; i < 10; i += 1) fireEvent.click(zoomIn)
    expect(canvas).toHaveAttribute('data-zoom', '1.4')
    expect(zoomIn).toBeDisabled()
    for (let i = 0; i < 10; i += 1) fireEvent.click(zoomOut)
    expect(canvas).toHaveAttribute('data-zoom', '0.8')
    expect(zoomOut).toBeDisabled()
    viewport.scrollLeft = 100; viewport.scrollTop = 40
    fireEvent.click(screen.getByRole('button', { name: 'Fit workspace' }))
    expect(canvas).toHaveAttribute('data-zoom', '1')
    expect(viewport.scrollLeft).toBe(0)
    expect(viewport.scrollTop).toBe(0)
    expect(screen.getByText('First result')).toBeVisible()
    expect(evidence).not.toHaveBeenCalled()
    expect(before.tasks[0].state).toBe('running')
  })
  it('navigates actual neighbours and distinguishes human review from failure and pending work', () => {
    const tasks = [
      { ...task, id: 'collect', role: 'collector', title: 'Collect data', state: 'succeeded' },
      { ...task, id: 'review', role: 'descriptive', title: 'Review analysis', state: 'awaiting_approval' },
      { ...task, id: 'validate', role: 'validator', title: 'Validate output', state: 'failed' },
      { ...task, id: 'publish', role: 'publish', title: 'Publish report', state: 'pending' },
    ]
    const { container } = render(<AgentCollaboration run={runFixture({ state: 'failed', tasks })} events={[]} interrupted={false} pipelines={null} onEvidence={vi.fn()} />)
    expect(container.querySelector('.agent-flow__group--failed')).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Previous stage' }))
    expect(screen.getByText('Human review required')).toBeVisible()
    expect(container.querySelector('.agent-flow__group--awaiting_approval')).toHaveAttribute('aria-pressed', 'true')
    fireEvent.click(screen.getByRole('button', { name: 'Previous stage' }))
    expect(screen.getByRole('button', { name: 'Previous stage' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Follow current stage' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next stage' }))
    expect(screen.getByRole('button', { name: 'Next stage' })).toBeDisabled()
    expect(container.querySelector('.agent-flow__group--pending')).toHaveAttribute('aria-pressed', 'true')
    expect(container.querySelector('.agent-flow__signal')).toBeNull()
  })
  it('pulses once for a new observed result and keeps its direction through view-only actions', () => {
    vi.useFakeTimers()
    const props = { interrupted: false, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} run={before} events={events} />)
    expect(container.querySelector('.agent-flow__signal')).toHaveAttribute('data-direction', 'outbound')
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    const returned = container.querySelector('.agent-flow__signal--updated')!
    expect(returned).toHaveAttribute('data-direction', 'inbound')
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }))
    fireEvent.click(screen.getByRole('button', { name: 'Follow current stage' }))
    expect(container.querySelector('.agent-flow__signal--updated')).toBe(returned)
    // jsdom exposes WebkitAnimation styles but no AnimationEvent constructor,
    // so React registers the prefixed event. Keep the fallback timer frozen:
    // only the matching path's animation-end handler can clear this pulse.
    const animationEnd = 'AnimationEvent' in window ? 'animationend' : 'webkitAnimationEnd'
    fireEvent(returned, new Event(animationEnd, { bubbles: true }))
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__signal')).toBe(returned)
    rerender(<AgentCollaboration {...props} run={{ ...after, paused: true }} events={later} />)
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-still', 'true')
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
  })
  it('consumes an unfinished pulse when hidden and only animates a new observed stage after returning', () => {
    const props = { interrupted: false, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} run={before} events={events} />)
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).not.toBeNull()
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    fireEvent(document, new Event('visibilitychange'))
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    hidden.mockReturnValue(false)
    fireEvent(document, new Event('visibilitychange'))
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__signal')).toHaveAttribute('data-direction', 'inbound')
    const next = { ...after, updated_at: '2026-10-16T10:02:00Z', tasks: [{ ...after.tasks[0], state: 'failed' }] }
    rerender(<AgentCollaboration {...props} run={next} events={appendEvents(later, snapshotEvents(after, next))} />)
    expect(container.querySelector('.agent-flow__signal--updated')).not.toBeNull()
  })
  it.each(['held', 'interrupted', 'run paused'])('does not replay a pulse after %s suppression is removed', (reason) => {
    const props = { interrupted: false, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} run={before} events={events} />)
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).not.toBeNull()
    if (reason === 'held') fireEvent.click(screen.getByRole('button', { name: 'Pause live view' }))
    else rerender(<AgentCollaboration {...props} interrupted={reason === 'interrupted'} run={{ ...after, paused: reason === 'run paused' }} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    if (reason === 'held') fireEvent.click(screen.getByRole('button', { name: 'Resume live view' }))
    else rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__signal')).toHaveAttribute('data-direction', 'inbound')
  })
  it.each(['app', 'system'])('consumes pending and newly observed motion under the %s reduced-motion preference', async (source) => {
    let systemReduced = false
    const media = new EventTarget()
    vi.stubGlobal('matchMedia', () => ({
      get matches() { return systemReduced },
      addEventListener: media.addEventListener.bind(media),
      removeEventListener: media.removeEventListener.bind(media),
    }))
    async function reduce(value: boolean) {
      await act(async () => {
        if (source === 'app') {
          if (value) document.documentElement.dataset.motion = 'reduce'
          else delete document.documentElement.dataset.motion
        } else { systemReduced = value; media.dispatchEvent(new Event('change')) }
      })
    }
    const props = { interrupted: false, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} run={before} events={events} />)
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).not.toBeNull()
    await reduce(true)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    await reduce(false)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    await reduce(true)
    const next = { ...after, updated_at: '2026-10-16T10:02:00Z', tasks: [{ ...after.tasks[0], state: 'failed' }] }
    rerender(<AgentCollaboration {...props} run={next} events={appendEvents(later, snapshotEvents(after, next))} />)
    await reduce(false)
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__signal')).toHaveAttribute('data-direction', 'inbound')
  })
  it('expires a pending pulse even when a hidden phone-layout SVG emits no animationend', () => {
    vi.useFakeTimers()
    const props = { interrupted: false, pipelines: null, onEvidence: vi.fn() }
    const { container, rerender } = render(<AgentCollaboration {...props} run={before} events={events} />)
    rerender(<AgentCollaboration {...props} run={after} events={later} />)
    expect(container.querySelector('.agent-flow__signal--updated')).not.toBeNull()
    act(() => { vi.advanceTimersByTime(900) })
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Pause live view' }))
    fireEvent.click(screen.getByRole('button', { name: 'Resume live view' }))
    expect(container.querySelector('.agent-flow__signal--updated')).toBeNull()
    expect(container.querySelector('.agent-flow__signal')).toHaveAttribute('data-direction', 'inbound')
  })
  it('leaves queued work quiet when no observation has arrived', () => {
    const { container } = render(<AgentCollaboration run={runFixture()} events={[]} interrupted={false} pipelines={null} onEvidence={vi.fn()} />)
    expect(container.querySelector('.agent-flow__signal')).toBeNull()
    expect(container.querySelector('.agent-flow__latest')).toBeNull()
    expect(container.querySelector('.agent-flow')).toHaveAttribute('data-working', 'false')
    expect(screen.getByText('Waiting for an observed update')).toBeVisible()
  })
})
