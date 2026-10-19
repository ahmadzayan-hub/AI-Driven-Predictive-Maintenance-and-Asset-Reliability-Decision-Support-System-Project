import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api } from '../../shared/api'
import type { RunExecutive, TableFilter } from '../../shared/types'
import { ExecutiveOverview } from './ExecutiveOverview'
import { executiveDrill, EMPTY, rolesOf, toFilters } from './state'
import { executiveMessages } from './executiveMessages'

vi.mock('../../shared/api', () => ({ api: { runExecutive: vi.fn() } }))

const snapshot = (): RunExecutive => ({
  run: { id: 'r1', dataset_name: 'maintenance.csv', state: 'awaiting_approval' }, language: 'en', source: 'engine',
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
})
afterEach(() => { act(() => applyLocale('en')); vi.restoreAllMocks(); vi.clearAllMocks(); vi.unstubAllGlobals() })

describe('executive decision overview', () => {
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
    expect(await screen.findByText('Below evaluation criteria')).toBeVisible()
    expect(screen.queryByText('Meets evaluation criteria')).not.toBeInTheDocument()
  })

  it('prepares a deterministic briefing on demand and downloads the same sourced snapshot', async () => {
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
    await user.click(screen.getByRole('button', { name: 'Download evidence brief (JSON)' }))
    expect(create).toHaveBeenCalledWith(expect.any(Blob))
    expect(click).toHaveBeenCalledOnce()
    expect(api.runExecutive).toHaveBeenCalledOnce()
    await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:executive'))
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

it('preserves every supported drill filter and refuses unrepresentable scopes', () => {
  const roles = rolesOf([{ name: 'site', type: 'text', role: null, records: 10, filled: 10 }, { name: 'month', type: 'text', role: 'date', records: 10, filled: 10 }, { name: 'loss', type: 'number', role: 'analysed', records: 10, filled: 10 }])
  const filters: TableFilter[] = [{ column: 'site', op: 'in', values: ['North', 'South'] }, { column: 'site', op: 'in', values: ['North'] }, { column: 'month', op: 'gte', value: '2026-01' }, { column: 'loss', op: 'lt', value: 100 }]
  const state = executiveDrill(filters, { ...EMPTY, offset: 25 }, roles)!
  expect(toFilters(state, roles.date, roles.measure)).toEqual([filters[1], filters[2], filters[3]])
  expect(state.offset).toBe(0)
  expect(executiveDrill([{ column: 'loss', op: 'ne', value: 5 }], EMPTY, roles)).toBeNull()
  expect(executiveDrill([{ column: 'site', op: 'in', values: ['North'] }, { column: 'site', op: 'in', values: ['South'] }], EMPTY, roles)).toBeNull()
})
