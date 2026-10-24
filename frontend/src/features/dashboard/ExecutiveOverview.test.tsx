import { act, cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api } from '../../shared/api'
import type { RunExecutive, TableFilter } from '../../shared/types'
import { ExecutiveOverview } from './ExecutiveOverview'
import { executiveDrill, EMPTY, rolesOf, toFilters } from './state'
import { executiveMessages } from './executiveMessages'

vi.mock('../../shared/api', () => ({ api: { runExecutive: vi.fn(), downloadExecutive: vi.fn() } }))

const snapshot = (): RunExecutive => ({
  snapshot_id: 'a'.repeat(64),
  run: { id: 'r1', dataset_name: 'maintenance.csv', state: 'awaiting_approval', updated_at: '2026-10-19T08:00:00Z' }, language: 'en', source: 'engine',
  scope: { records: 3, total_records: 10, filters: [{ column: 'site', op: 'in', values: ['North'] }] },
  headline: 'Review missing downtime before deciding.', readiness: { status: 'limited', limitations: ['Two downtime readings are missing.'] },
  kpis: { measures: [{ key: 'downtime', title: 'Downtime', value: null, scale: 'hours', numerator: 0, denominator: 0, formula: 'sum(downtime)', population: 'Selected work orders', records: 1, records_excluded: 0, records_unmeasured: 2, missing_policy: 'Exclude absent readings', undefined_reason: 'Insufficient readings', edge_cases: '' }], unavailable: { availability: 'Operating hours are required.' } },
  priorities: [{ id: 'p1', title: 'Review North work orders', detail: 'Inspect the selected source records.', evidence_refs: ['scope.records'], drilldown_id: 'd1' }],
  questions: [{ id: 'q1', text: 'Who will verify the missing readings?', evidence_refs: ['scope.records'] }],
  findings: [{ id: 'f1', text: 'Original analysis finding', stage: 'preparer', kind: 'warning', evidence_refs: ['scope.records'], scope: 'whole_run' }],
  models: [{ kind: 'maintenance_risk', target: 'Repeat failures', fitted: false, details: { reason: 'Too few labelled records' }, scope: 'whole_run' }],
  evidence: [{ id: 'scope.records', kind: 'scope', label: 'Selected records', value: 3, method: 'Count after filters', scope: 'filtered' }],
  drilldowns: [{ id: 'd1', label: 'Inspect North work orders', filters: [{ column: 'site', op: 'in', values: ['North'] }] }],
})

function mount(filters: TableFilter[] = []) {
  const props = { runId: 'r1', filters, onOpenRun: vi.fn(), onDrill: vi.fn(), canDrill: () => true, children: <p>Selected-record chart</p> }
  return { ...render(<ExecutiveOverview {...props} />), props }
}
beforeEach(() => {
  applyLocale('en')
  vi.mocked(api.runExecutive).mockResolvedValue(snapshot())
  vi.mocked(api.downloadExecutive).mockResolvedValue({ blob: new Blob(['<html>Report</html>'], { type: 'text/html' }), name: 'report.html' })
})
afterEach(() => { cleanup(); act(() => applyLocale('en')); vi.restoreAllMocks(); vi.clearAllMocks(); vi.unstubAllGlobals() })

describe('executive decision overview', () => {
  it('leads the prepared brief with the maintenance mandate, decisions and source boundaries', async () => {
    const data = snapshot()
    data.advisory = {
      title: 'AI-Driven Predictive Maintenance and Asset Reliability Decision-Support System',
      subtitle: 'Condition, failures, work orders, downtime and economic impact', role: 'Executive Analytics Advisory Group',
      recommendation: 'Commission a reliability review before approving intervention spend.', prediction: 'Future prediction is not validated.',
      domains: [{ id: 'condition', title: 'Condition', measure: 'Mean recorded condition score', value: 80, scale: 'score', status: 'unassessed', reason: 'Thresholds require confirmation.', records: 2, unmeasured: 1, implication: 'Confirm when readings were recorded.', evidence_refs: ['scope.records'] }],
      decisions: [{ id: 'p1', title: 'Review North work orders', action: 'Inspect the selected source records.', owner: 'Reliability engineer', gate: 'Before approving a maintenance intervention', evidence_refs: ['scope.records'] }],
      sources: [{ id: 'workbook', title: 'Supporting analytics workbook', status: 'unassessed', detail: 'Reconciliation is not recorded.' }],
      new_findings: 'Selected calculations are separate from reference material.', preservation: 'Preserve the approved master dataset.', escalation: 'Consult instructors before changing business rules.',
    }
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    await screen.findByRole('heading', { name: 'Executive overview' })
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Prepare executive brief' }))
    expect(screen.getByText(data.advisory.recommendation)).toBeVisible()
    expect(screen.getByText(/Proposed accountable role: Reliability engineer/)).toBeVisible()
    expect(screen.getByText('Future prediction is not validated.')).toBeVisible()
    await user.click(screen.getByText('Analytical basis and source reconciliation'))
    expect(screen.getByText('Preserve the approved master dataset.')).toBeVisible()
    expect(screen.getByText('Reconciliation is not recorded.')).toBeVisible()
    expect(screen.getByText('Consult instructors before changing business rules.')).toBeVisible()
  })
  it('groups measures by the register family, keeps verdict reasons on the card and moves "no target" into the evidence', async () => {
    const base = snapshot().kpis.measures[0]
    const data = snapshot()
    data.kpis.measures = [
      { ...base, key: 'first_time_fix', title: 'First-time fix', family: 'execution', value: 57.5, scale: 'percent', records: 2, records_unmeasured: 0,
        assessment: { status: 'unassessed', reason: 'No display target is configured.', reason_code: 'no_target', direction: null, source_ref: null, rule_id: null, thresholds: null } },
      { ...base, key: 'availability', title: 'Availability', family: 'reliability', value: 90, scale: 'percent', records: 3, records_unmeasured: 0,
        assessment: { status: 'bad', reason: 'Below the 95% target.', reason_code: 'below', direction: 'higher', thresholds: { good_at: 95, okay_at: 92 }, source_ref: 'Fictional QA', rule_id: 'r1' } },
      { ...base, key: 'mtbf', title: 'Mean time between failures', family: 'reliability', value: 48, scale: 'hours', records: 3, records_unmeasured: 0,
        assessment: { status: 'unassessed', reason: 'Set for an earlier definition; review it.', reason_code: 'target_outdated', direction: 'higher', thresholds: { good_at: 40, okay_at: 30 }, source_ref: 'Fictional QA', rule_id: 'r2' } },
    ]
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    await screen.findByRole('heading', { name: 'Availability' })
    const families = [...document.querySelectorAll('.exec-family > h4')]
    expect(families.map((heading) => heading.textContent)).toEqual(['Reliability', 'Work execution'])
    const availability = screen.getByRole('heading', { name: 'Availability' }).closest('article')!
    expect(availability.closest('section')).toHaveAttribute('data-family', 'reliability')
    expect(within(availability).getByText('Below the 95% target.')).toBeVisible()
    expect(availability.querySelector('.exec-kpi-meter rect + rect')).toHaveAttribute('width', '90')
    const fix = screen.getByRole('heading', { name: 'First-time fix' }).closest('article')!
    const reason = within(fix).getByText('No display target is configured.')
    expect(reason.closest('details')).not.toBeNull()
    expect(reason).not.toBeVisible()
    const mtbf = screen.getByRole('heading', { name: 'Mean time between failures' }).closest('article')!
    expect(mtbf.querySelector('.exec-kpi-meter')).toBeNull()
    // A target held for review is said on the card, not hidden in the evidence.
    const review = within(mtbf).getByText('Set for an earlier definition; review it.')
    expect(review).toBeVisible()
    expect(review.closest('details')).toBeNull()
    // The unit stays on the number's line: a non-breaking space joins them.
    expect(mtbf.querySelector('.exec-kpi-value bdi')!.textContent).toMatch(/\d\u00a0h$/)
  })

  it('uses the requested scope, exposes missing evidence and keeps unfitted models unscored', async () => {
    const user = userEvent.setup()
    const filters: TableFilter[] = [{ column: 'site', op: 'in', values: ['North'] }]
    const { props } = mount(filters)
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(api.runExecutive).toHaveBeenCalledWith('r1', 'en', filters, expect.any(AbortSignal))
    expect(screen.getByText('of 10 cleaned records')).toBeVisible()
    const kpi = screen.getByRole('heading', { name: 'Downtime' }).closest('article')!
    expect(within(kpi).getByText('Not available')).toBeVisible()
    expect(within(kpi).getByText('2 records without a reading')).toBeVisible()
    expect(screen.getByRole('region', { name: 'Model evaluation data' })).not.toBeVisible()
    await user.click(screen.getByText('Model quality · Whole analysis'))
    const modelTable = within(screen.getByRole('region', { name: 'Model evaluation data' }))
    expect(modelTable.getByText('Not evaluated')).toBeVisible()
    expect(modelTable.getAllByRole('cell', { name: '—' })).toHaveLength(2)
    expect(screen.getByText(/filters do not retrain/)).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Inspect North work orders' }))
    expect(props.onDrill).toHaveBeenCalledWith(filters)
    await user.click(screen.getAllByRole('button', { name: 'View evidence (1)' })[0])
    expect(screen.getByRole('region', { name: 'Evidence register' })).toBeVisible()
    expect(screen.getByRole('cell', { name: /Count after filters/ })).toBeVisible()
    expect(screen.getByRole('row', { name: /scope.records/ })).toHaveFocus()
    screen.getByRole('button', { name: 'Inspect North work orders' }).focus()
    await user.click(screen.getAllByRole('button', { name: 'View evidence (1)' })[0])
    expect(screen.getByRole('row', { name: /scope.records/ })).toHaveFocus()
  })

  it('preserves a weak verdict even when a model beats its baseline numerically', async () => {
    const data = snapshot()
    data.models = [{ kind: 'maintenance_risk', target: 'Failure', fitted: true, beats_baseline: true, metric: { name: 'balanced_accuracy', model: .53, baseline: .5, baseline_name: 'majority' }, details: { verdict: 'weak' }, scope: 'whole_run' }]
    vi.mocked(api.runExecutive).mockResolvedValueOnce(data)
    mount()
    expect(await screen.findByText('Below evaluation criteria')).not.toBeVisible()
    await userEvent.setup().click(screen.getByText('Model quality · Whole analysis'))
    expect(screen.getByText('Below evaluation criteria')).toBeVisible()
    expect(screen.queryByText('Meets evaluation criteria')).not.toBeInTheDocument()
  })

  it('prepares a deterministic briefing and downloads authenticated HTML for the captured scope and timestamp', async () => {
    const user = userEvent.setup()
    const create = vi.fn(() => 'blob:executive')
    const revoke = vi.fn()
    vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    mount()
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(screen.queryByText('Who will verify the missing readings?')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Prepare executive brief' }))
    expect(screen.getByRole('region', { name: 'Brief prepared for the current scope' })).toHaveTextContent('Who will verify the missing readings?')
    expect(screen.getAllByText('Deterministic · governed evidence').length).toBeGreaterThan(0)
    expect(screen.getByRole('combobox', { name: 'Report format' })).toHaveValue('html')
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    expect(api.downloadExecutive).toHaveBeenCalledWith('r1', 'en', snapshot().scope.filters, snapshot().run.updated_at, snapshot().snapshot_id, 'html', expect.any(AbortSignal))
    expect(create).toHaveBeenCalledWith(expect.any(Blob))
    expect(click).toHaveBeenCalledOnce()
    expect(api.runExecutive).toHaveBeenCalledOnce()
    const anchor = click.mock.instances[0] as HTMLAnchorElement
    expect(anchor.download).toBe('report.html')
    await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:executive'), { timeout: 2_000 })
  })

  it('keeps a stored unsupported verdict neutral even when a stale metric and positive flag are present', async () => {
    const data = snapshot()
    data.models = [{ kind: 'maintenance_risk', target: 'Failure', fitted: true, beats_baseline: true, metric: { name: 'balanced_accuracy', model: .99, baseline: .5, baseline_name: 'majority' }, details: { verdict: 'not_supported' }, scope: 'whole_run' }]
    vi.mocked(api.runExecutive).mockResolvedValueOnce(data)
    mount()
    expect(await screen.findByText('Not evaluated')).toHaveAttribute('data-performance', 'unassessed')
    expect(screen.queryByText('0.99 / 0.5')).not.toBeInTheDocument()
    expect(screen.queryByText('Meets evaluation criteria')).not.toBeInTheDocument()
  })

  it('shows a recoverable API failure without invented figures', async () => {
    vi.mocked(api.runExecutive).mockRejectedValueOnce(new Error('unavailable'))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded')
    expect(screen.queryByText('of 10 cleaned records')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(api.runExecutive).toHaveBeenCalledTimes(2)
  })

  it('aborts a changed scope and ignores a late response rather than replacing current figures', async () => {
    let finishOld!: (value: RunExecutive) => void
    vi.mocked(api.runExecutive).mockImplementationOnce(() => new Promise((resolve) => { finishOld = resolve }))
    const { rerender, props } = mount()
    await waitFor(() => expect(api.runExecutive).toHaveBeenCalledOnce())
    const signal = vi.mocked(api.runExecutive).mock.calls[0][3]!
    const filtered = { ...snapshot(), headline: 'Current South scope', scope: { records: 1, total_records: 10, filters: [] } }
    vi.mocked(api.runExecutive).mockResolvedValueOnce(filtered)
    rerender(<ExecutiveOverview {...props} filters={[{ column: 'site', op: 'in', values: ['South'] }]} />)
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(signal.aborted).toBe(true)
    await act(async () => finishOld(snapshot()))
    await userEvent.click(screen.getByRole('button', { name: 'Prepare executive brief' }))
    expect(screen.getByText('Current South scope')).toBeVisible()
    expect(screen.queryByText('Review missing downtime before deciding.')).not.toBeInTheDocument()
  })

  it('hides prepared content when language changes and renders Arabic RTL', async () => {
    const user = userEvent.setup()
    mount()
    await user.click(await screen.findByRole('button', { name: 'Prepare executive brief' }))
    const arabic: RunExecutive = { ...snapshot(), language: 'ar', headline: 'راجع أدلة التوقف قبل القرار.' }
    vi.mocked(api.runExecutive).mockResolvedValueOnce(arabic)
    act(() => applyLocale('ar'))
    const heading = await screen.findByRole('heading', { name: 'النظرة التنفيذية' })
    expect(heading.closest('.exec-overview')).toHaveAttribute('dir', 'rtl')
    expect(screen.getByRole('button', { name: 'إعداد الموجز التنفيذي' })).toBeVisible()
    expect(screen.queryByText('Who will verify the missing readings?')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'إعداد الموجز التنفيذي' }))
    expect(screen.getByText('راجع أدلة التوقف قبل القرار.')).toBeVisible()
    expect(Object.keys(executiveMessages.en)).toEqual(Object.keys(executiveMessages.ar))
  })

  it('refreshes the captured timestamp with the returned snapshot and discards the previous brief', async () => {
    const first = snapshot()
    first.run.updated_at = '2026-10-19T08:00:00Z'
    const second = snapshot()
    second.run.updated_at = '2026-10-19T09:30:00Z'
    second.headline = 'Refreshed evidence'
    vi.mocked(api.runExecutive).mockResolvedValueOnce(first).mockResolvedValueOnce(second)
    const user = userEvent.setup()
    const { container } = mount()
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(container.querySelector('time')).toHaveAttribute('datetime', first.run.updated_at)
    await user.click(screen.getByRole('button', { name: 'Prepare executive brief' }))
    await user.click(screen.getByRole('button', { name: 'Refresh overview' }))
    await screen.findByRole('heading', { name: 'Executive overview' })
    expect(container.querySelector('time')).toHaveAttribute('datetime', second.run.updated_at)
    expect(screen.queryByText('Review missing downtime before deciding.')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Prepare executive brief' }))
    expect(screen.getByText('Refreshed evidence')).toBeVisible()
  })
})

function mockObjectUrls() {
  const create = vi.fn(() => 'blob:report')
  const revoke = vi.fn()
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke })
  return { create, revoke }
}

function mockPopup(fonts: Promise<unknown> = Promise.resolve()) {
  const events = new EventTarget()
  const popup = Object.assign(events, {
    closed: false, opener: {} as unknown,
    location: { href: 'about:blank' }, document: { URL: 'about:blank', readyState: 'loading', fonts: { ready: fonts } },
    focus: vi.fn(), close: vi.fn(), print: vi.fn(),
  })
  popup.close.mockImplementation(() => { popup.closed = true })
  popup.print.mockImplementation(() => popup.dispatchEvent(new Event('afterprint')))
  vi.spyOn(window, 'open').mockReturnValue(popup as unknown as Window)
  return popup
}

async function prepare() {
  const user = userEvent.setup()
  await user.click(await screen.findByRole('button', { name: 'Prepare executive brief' }))
  return user
}

describe('business report export lifecycle', () => {
  it('keeps Arabic report selection, request language and stale-state recovery localized', async () => {
    applyLocale('ar')
    const data = snapshot()
    data.language = 'ar'
    vi.mocked(api.runExecutive).mockResolvedValueOnce(data)
    vi.mocked(api.downloadExecutive).mockRejectedValueOnce(Object.assign(new Error('stale'), { status: 409 }))
    mount()
    const user = userEvent.setup()
    await user.click(await screen.findByRole('button', { name: 'إعداد الموجز التنفيذي' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'تنسيق التقرير' }), 'docx')
    await user.click(screen.getByRole('button', { name: 'تنزيل التقرير' }))
    expect(api.downloadExecutive).toHaveBeenCalledWith('r1', 'ar', data.scope.filters, data.run.updated_at, data.snapshot_id, 'docx', expect.any(AbortSignal))
    expect(await screen.findByRole('alert')).toHaveTextContent('حدّث النظرة التنفيذية وأعد إعداد الموجز')
    expect(screen.getByRole('button', { name: 'طباعة / حفظ بصيغة PDF' })).toBeVisible()
  })

  it('downloads a real Word response with the prepared language, filters and revision', async () => {
    mockObjectUrls()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(api.downloadExecutive).mockResolvedValueOnce({ blob: new Blob(['docx bytes'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }), name: 'report.docx' })
    mount()
    const user = await prepare()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Report format' }), 'docx')
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    await waitFor(() => expect(click).toHaveBeenCalledOnce())
    expect(api.downloadExecutive).toHaveBeenCalledWith('r1', 'en', snapshot().scope.filters, snapshot().run.updated_at, snapshot().snapshot_id, 'docx', expect.any(AbortSignal))
    expect((click.mock.instances[0] as HTMLAnchorElement).download).toBe('report.docx')
    expect(screen.queryByText(/JSON/)).not.toBeInTheDocument()
  })

  it('retains the prepared brief on a download error and permits a retry', async () => {
    const { create } = mockObjectUrls()
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(api.downloadExecutive).mockRejectedValueOnce(new Error('network failed'))
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Your brief and filters are preserved')
    expect(screen.getByText('Who will verify the missing readings?')).toBeVisible()
    expect(create).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    await waitFor(() => expect(create).toHaveBeenCalledOnce())
    expect(api.downloadExecutive).toHaveBeenCalledTimes(2)
  })

  it('announces a server stale-snapshot conflict and requires refresh before a new prepared snapshot', async () => {
    vi.mocked(api.downloadExecutive).mockRejectedValueOnce(Object.assign(new Error('changed'), { status: 409 }))
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Refresh the overview and prepare the brief again')
    expect(screen.getByText('Who will verify the missing readings?')).toBeVisible()
    await user.click(within(screen.getByRole('alert').parentElement!).getByRole('button', { name: 'Refresh overview' }))
    await screen.findByRole('button', { name: 'Prepare executive brief' })
    expect(screen.queryByText('Who will verify the missing readings?')).not.toBeInTheDocument()
  })

  it('refuses an unversioned snapshot without requesting a file or opening a popup', async () => {
    const data = snapshot()
    data.run.updated_at = null
    vi.mocked(api.runExecutive).mockResolvedValueOnce(data)
    const open = vi.spyOn(window, 'open')
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('has no verifiable content revision')
    expect(api.downloadExecutive).not.toHaveBeenCalled()
    expect(open).not.toHaveBeenCalled()
  })

  it('refuses a snapshot without its content revision even when its timestamp is present', async () => {
    const data = snapshot()
    delete data.snapshot_id
    vi.mocked(api.runExecutive).mockResolvedValueOnce(data)
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('has no verifiable content revision')
    expect(api.downloadExecutive).not.toHaveBeenCalled()
  })

  it('aborts export on scope change and never downloads a late response', async () => {
    let complete!: (value: { blob: Blob; name: string }) => void
    vi.mocked(api.downloadExecutive).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve }))
    const { create } = mockObjectUrls()
    const { rerender, props } = mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    expect(screen.getByRole('button', { name: 'Download report' })).toBeDisabled()
    const signal = vi.mocked(api.downloadExecutive).mock.calls[0][6]!
    rerender(<ExecutiveOverview {...props} filters={[{ column: 'site', op: 'in', values: ['South'] }]} />)
    await screen.findByRole('button', { name: 'Prepare executive brief' })
    expect(signal.aborted).toBe(true)
    await act(async () => complete({ blob: new Blob(['old report']), name: 'old.html' }))
    expect(create).not.toHaveBeenCalled()
  })

  it('cancels an export when refreshing the overview revision', async () => {
    let complete!: (value: { blob: Blob; name: string }) => void
    vi.mocked(api.downloadExecutive).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve }))
    const { create } = mockObjectUrls()
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Download report' }))
    const signal = vi.mocked(api.downloadExecutive).mock.calls[0][6]!
    await user.click(screen.getByRole('button', { name: 'Refresh overview' }))
    await screen.findByRole('button', { name: 'Prepare executive brief' })
    expect(signal.aborted).toBe(true)
    await act(async () => complete({ blob: new Blob(['old revision']), name: 'old.html' }))
    expect(create).not.toHaveBeenCalled()
  })

  it('reports a blocked print popup without fetching or pretending a PDF was downloaded', async () => {
    vi.spyOn(window, 'open').mockReturnValue(null)
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Allow popups for this site')
    expect(screen.getByText(/not a direct PDF download/)).toBeVisible()
    expect(api.downloadExecutive).not.toHaveBeenCalled()
  })

  it('prints the completed blob document without a load event, waits for fonts and cleans up once', async () => {
    let ready!: () => void
    const fonts = new Promise<void>((resolve) => { ready = resolve })
    const popup = mockPopup(fonts)
    const readFonts = vi.fn(() => ({ ready: fonts }))
    Object.defineProperty(popup.document, 'fonts', { get: readFonts })
    const { create, revoke } = mockObjectUrls()
    mount()
    const user = await prepare()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Report format' }), 'docx')
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    expect(window.open).toHaveBeenCalledWith('', '_blank')
    expect(popup.opener).toBeNull()
    expect(api.downloadExecutive).toHaveBeenCalledWith('r1', 'en', snapshot().scope.filters, snapshot().run.updated_at, snapshot().snapshot_id, 'html', expect.any(AbortSignal))
    await waitFor(() => expect(popup.location.href).toBe('blob:report'))
    expect(create).toHaveBeenCalledOnce()
    expect(revoke).not.toHaveBeenCalled()
    // The initial about:blank listener is gone: no load event is dispatched.
    popup.document.URL = 'blob:report'
    popup.document.readyState = 'complete'
    await waitFor(() => expect(readFonts).toHaveBeenCalledOnce())
    expect(popup.print).not.toHaveBeenCalled()
    await act(async () => ready())
    expect(popup.print).toHaveBeenCalledOnce()
    expect(popup.close).toHaveBeenCalledOnce()
    expect(revoke).toHaveBeenCalledWith('blob:report')
    expect(screen.getByText(/A PDF is saved only if you chose/)).toBeVisible()
  })

  it('does not print a late font-ready result after cancellation', async () => {
    let ready!: () => void
    const fonts = new Promise<void>((resolve) => { ready = resolve })
    const popup = mockPopup(fonts)
    const readFonts = vi.fn(() => ({ ready: fonts }))
    Object.defineProperty(popup.document, 'fonts', { get: readFonts })
    const { revoke } = mockObjectUrls()
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    await waitFor(() => expect(popup.location.href).toBe('blob:report'))
    popup.document.URL = 'blob:report'
    popup.document.readyState = 'complete'
    await waitFor(() => expect(readFonts).toHaveBeenCalledOnce())
    await user.click(screen.getByRole('button', { name: 'Cancel export' }))
    await act(async () => ready())
    expect(popup.print).not.toHaveBeenCalled()
    expect(popup.close).toHaveBeenCalledOnce()
    expect(revoke).toHaveBeenCalledWith('blob:report')
  })

  it('cancels a pending print fetch, closes its blank popup and discards the late file', async () => {
    let complete!: (value: { blob: Blob; name: string }) => void
    vi.mocked(api.downloadExecutive).mockImplementationOnce(() => new Promise((resolve) => { complete = resolve }))
    const popup = mockPopup()
    const { create } = mockObjectUrls()
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    const signal = vi.mocked(api.downloadExecutive).mock.calls[0][6]!
    await user.click(screen.getByRole('button', { name: 'Cancel export' }))
    expect(signal.aborted).toBe(true)
    expect(popup.closed).toBe(true)
    expect(screen.getByText('Export cancelled.')).toBeVisible()
    await act(async () => complete({ blob: new Blob(['late']), name: 'late.html' }))
    expect(create).not.toHaveBeenCalled()
  })

  it('aborts and closes a pending preview when the component unmounts', async () => {
    vi.mocked(api.downloadExecutive).mockImplementationOnce(() => new Promise(() => {}))
    const popup = mockPopup()
    const { unmount } = mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    const signal = vi.mocked(api.downloadExecutive).mock.calls[0][6]!
    unmount()
    expect(signal.aborted).toBe(true)
    expect(popup.close).toHaveBeenCalledOnce()
  })

  it('announces a manually closed preview and aborts the pending request', async () => {
    vi.mocked(api.downloadExecutive).mockImplementationOnce(() => new Promise(() => {}))
    const popup = mockPopup()
    mount()
    const user = await prepare()
    await user.click(screen.getByRole('button', { name: 'Print / Save as PDF' }))
    popup.closed = true
    await screen.findByText('Print preview closed.')
    expect(vi.mocked(api.downloadExecutive).mock.calls[0][6]!.aborted).toBe(true)
    expect(screen.getByRole('button', { name: 'Download report' })).toBeEnabled()
  })
})

it('preserves every supported drill filter and refuses unrepresentable scopes', () => {
  const roles = rolesOf([{ name: 'site', type: 'text', role: null, records: 10, filled: 10 }, { name: 'month', type: 'text', role: 'date', records: 10, filled: 10 }, { name: 'loss', type: 'number', role: 'analysed', records: 10, filled: 10 }])
  const filters: TableFilter[] = [{ column: 'site', op: 'in', values: ['North', 'South'] }, { column: 'site', op: 'in', values: ['North'] }, { column: 'month', op: 'gte', value: '2026-01' }, { column: 'loss', op: 'lt', value: 100 }]
  const state = executiveDrill(filters, { ...EMPTY, offset: 25 }, roles)!
  expect(toFilters(state, roles.date, roles.measure)).toEqual([filters[1], filters[2], filters[3]])
  expect(state.offset).toBe(0)
  expect(executiveDrill([{ column: 'loss', op: 'ne', value: 5 }], EMPTY, roles)).toBeNull()
  expect(executiveDrill([{ column: 'site', op: 'in', values: ['North'] }, { column: 'site', op: 'in', values: ['South'] }], EMPTY, roles)).toBeNull()
})


describe('KPI review context', () => {
  it('links the exact scoped evidence without treating analysis time or advisory roles as measurement metadata', async () => {
    const data = snapshot()
    data.evidence.push({ id: 'executive.kpi.downtime', kind: 'kpi', label: 'Downtime calculation', value: null, method: 'Verified fixture method', scope: 'filtered' })
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    const { props } = mount()
    const card = (await screen.findByRole('heading', { name: 'Downtime' })).closest('article')!
    const user = userEvent.setup()
    expect(within(card).getByText('Period/owner unknown; freshness unassessed. Update ≠ observation.')).toBeVisible()
    await user.click(within(card).getByText('Inspect evidence'))
    expect(within(card).getByText('maintenance.csv')).toBeVisible()
    expect(within(card).getByText(data.run.id)).toBeVisible()
    expect(within(card).getByText(/Who reviews/)).toBeVisible()
    await user.click(within(card).getByRole('button', { name: 'View evidence (1)' }))
    expect(screen.getByRole('row', { name: /executive.kpi.downtime/ })).toHaveFocus()
    await user.click(screen.getByRole('button', { name: 'Open the analysis' }))
    expect(props.onOpenRun).toHaveBeenCalledOnce()
  })

  it.each([NaN, Infinity, -Infinity, undefined])('keeps invalid numeric input %s unavailable without a meter', async (value) => {
    const data = snapshot()
    data.kpis.measures[0].value = value as number
    data.kpis.measures[0].scale = 'percent'
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    const card = (await screen.findByRole('heading', { name: 'Downtime' })).closest('article')!
    expect(within(card).getByText('Not available')).toBeVisible()
    expect(card.querySelector('.exec-kpi-meter')).toBeNull()
    expect(card.querySelector('.performance-value')).toHaveAttribute('data-performance', 'unavailable')
    expect(card.querySelector('.exec-kpi-n')).not.toHaveTextContent(/NaN|Infinity/)
  })

  it('preserves a measured zero and does not fabricate absent source metadata', async () => {
    const data = snapshot()
    data.kpis.measures[0].value = 0
    data.kpis.measures[0].scale = 'percent'
    delete data.snapshot_id
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    const card = (await screen.findByRole('heading', { name: 'Downtime' })).closest('article')!
    expect(card.querySelector('.exec-kpi-n')).toHaveTextContent('0')
    expect(card.querySelector('.exec-kpi-meter rect + rect')).toHaveAttribute('width', '0')
    await userEvent.setup().click(within(card).getByText('Inspect evidence'))
    expect(within(card).queryByRole('button', { name: 'View evidence (1)' })).not.toBeInTheDocument()
    expect(within(card).getByText('Evidence register: Not available')).toBeVisible()
  })

  it.each([['kpi', 'whole_run'], ['calculation', 'filtered']] as const)('rejects mismatched evidence kind=%s scope=%s independently', async (kind, scope) => {
    const data = snapshot()
    data.evidence.push({ id: 'executive.kpi.downtime', kind, label: 'Other scope', value: 1, method: 'Mismatched evidence', scope })
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    const card = (await screen.findByRole('heading', { name: 'Downtime' })).closest('article')!
    await userEvent.setup().click(within(card).getByText('Inspect evidence'))
    expect(within(card).queryByRole('button', { name: 'View evidence (1)' })).not.toBeInTheDocument()
  })

  it('renders the same accountable-owner question and honest unknowns in Arabic RTL', async () => {
    applyLocale('ar')
    const data = snapshot(); data.kpis.measures[0].title = 'مدة التعطل'
    vi.mocked(api.runExecutive).mockResolvedValue(data)
    mount()
    const card = (await screen.findByRole('heading', { name: 'مدة التعطل' })).closest('article')!
    expect(card.closest('.exec-overview')).toHaveAttribute('dir', 'rtl')
    await userEvent.setup().click(within(card).getByText(executiveMessages.ar['exec.sources']))
    expect(within(card).getByText('من يراجع «مدة التعطل»؟')).toBeVisible()
    expect(within(card).getByText(executiveMessages.ar['exec.contextUnconfirmed'])).toBeVisible()
    expect(screen.getByRole('button', { name: 'فتح التحليل' })).toBeVisible()
  })
})
