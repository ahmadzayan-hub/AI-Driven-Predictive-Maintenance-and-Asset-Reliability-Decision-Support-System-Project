import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api, ApiError } from '../../shared/api'
import { DashboardView } from './DashboardView'
import type { ReactNode } from 'react'
import { dashMessages } from './messages'

vi.mock('./ExecutiveOverview', () => ({ ExecutiveOverview: ({ children }: { children: ReactNode }) => <>{children}</> }))

vi.mock('../../shared/api', async (original) => {
  const actual = await original<typeof import('../../shared/api')>()
  return { ...actual, api: { ...actual.api, listRuns: vi.fn(), tableFields: vi.fn(), getRun: vi.fn(), queryTable: vi.fn(), tableRecords: vi.fn(), getDashboardView: vi.fn(), saveDashboardView: vi.fn(), forgetDashboardView: vi.fn() } }
})
beforeEach(() => {
  applyLocale('en')
  vi.clearAllMocks()
  vi.mocked(api.tableFields).mockResolvedValue({ records: 1, fields: [{ name: 'label', type: 'text', role: null, filled: 1, records: 1 }] })
  vi.mocked(api.getRun).mockRejectedValue(new ApiError('Not found', 404))
  vi.mocked(api.queryTable).mockResolvedValue({ groups: [], group_by: [], measures: [], group_count: 0, truncated: false, records: 1, matched_records: 1 })
  vi.mocked(api.tableRecords).mockResolvedValue({ columns: ['label'], rows: [['Owner A fixture']], total: 1 })
  vi.mocked(api.getDashboardView).mockResolvedValue({ view: null })
})

it.each(['en', 'ar'] as const)('keeps numeric-only uploads quantitative with an honest distribution (%s)', async (locale) => {
  applyLocale(locale)
  vi.mocked(api.tableFields).mockResolvedValue({ records: 3, fields: [
    { name: 'cost', type: 'number', role: 'analysed', filled: 3, records: 3 },
  ] })
  vi.mocked(api.queryTable).mockImplementation(async (_id, spec) => ({
    groups: spec.group_by?.length ? [
      { keys: [[0, 10]], values: [1], records: 1 },
      { keys: [[10, 20]], values: [2], records: 2 },
    ] : [], group_by: [], measures: [], group_count: 2, truncated: false, records: 3, matched_records: 3,
  }))
  const view = render(<DashboardView runId="r1" page="overview" query="" onNavigate={vi.fn()} onOpenRun={vi.fn()} />)
  expect(await screen.findByRole('img')).toBeVisible()
  expect(screen.getByText(dashMessages[locale]['dash.numericContext'])).toBeVisible()
  expect(screen.getByRole('table')).toHaveTextContent('0 – 10')
  expect(screen.getByRole('table')).toHaveTextContent('10 – 20')
  expect(vi.mocked(api.queryTable).mock.calls.some(([, spec]) => JSON.stringify(spec.group_by) === JSON.stringify([{ column: 'cost', bins: 12 }]))).toBe(true)
  view.unmount()
})

it('does not reuse private answers after the dashboard is unmounted for an identity change', async () => {
  const props = { runId: 'r1', page: 'records', query: '', onNavigate: vi.fn(), onOpenRun: vi.fn() }
  const first = render(<DashboardView {...props} />)
  expect(await screen.findByRole('cell', { name: 'Owner A fixture' })).toBeVisible()
  first.unmount()
  vi.mocked(api.tableFields).mockRejectedValueOnce(new ApiError('Access denied', 403))
  render(<DashboardView {...props} />)
  expect(await screen.findByRole('alert')).toHaveTextContent('Access denied')
  expect(screen.queryByText('Owner A fixture')).not.toBeInTheDocument()
  expect(api.tableFields).toHaveBeenCalledTimes(2)
})

it('offers maintenance intake and retries a failed analysis picker rather than reporting an empty workspace', async () => {
  const user = userEvent.setup()
  vi.mocked(api.listRuns).mockRejectedValueOnce(new ApiError('Unavailable', 503)).mockResolvedValueOnce({ runs: [{ id: 'r2', state: 'awaiting_approval', goal: 'Synthetic maintenance analysis', dataset_name: 'sample.csv', created_at: '', updated_at: '' }] })
  const onNavigate = vi.fn()
  render(<DashboardView runId={null} page={null} query="" onNavigate={onNavigate} onOpenRun={vi.fn()} />)
  expect(screen.getByRole('link', { name: 'Analyse maintenance data' })).toHaveAttribute('href', '#/datasets')
  expect(await screen.findByRole('alert')).toHaveTextContent('could not be loaded')
  expect(screen.queryByText(/No analysis has a cleaned table/)).not.toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await user.click(await screen.findByRole('button', { name: /Synthetic maintenance analysis/ }))
  expect(onNavigate).toHaveBeenCalledWith({ tab: 'dashboard', runId: 'r2' })
})

it.each(['overview', 'trend'])('discloses omitted later periods on the %s page in both languages', async (page) => {
  vi.mocked(api.tableFields).mockResolvedValue({ records: 1001, fields: [
    { name: 'day', type: 'text', role: 'date', filled: 1001, records: 1001 },
    { name: 'cost', type: 'number', role: 'analysed', filled: 1001, records: 1001 },
  ] })
  vi.mocked(api.queryTable).mockImplementation(async (_id, spec) => ({
    // Exercise the server's truncation contract with a small returned page.
    // Backend query tests own the row limit; this check owns the EN/AR notice.
    groups: spec.group_by?.length ? Array.from({ length: 3 }, (_, index) => ({ keys: [`period-${index}`], values: [1, 1, 1], records: 1 })) : [],
    group_by: [], measures: [], group_count: spec.group_by?.length ? 1001 : 1,
    truncated: Boolean(spec.group_by?.length), records: 1001, matched_records: 1001,
  }))
  for (const locale of ['en', 'ar'] as const) {
    applyLocale(locale)
    const view = render(<DashboardView runId="r1" page={page} query="" onNavigate={vi.fn()} onOpenRun={vi.fn()} />)
    const expected = dashMessages[locale]['dash.trendTruncated'].replace('{shown}', '3').replace('{total}', '1,001')
    expect(await screen.findByText(expected)).toBeVisible()
    view.unmount()
  }
}, 15000)

// Cross-filtering by clicking and a saved view per dataset (ADR
// 2026-10-27-interactive-dashboard).
const REGIONS = { records: 4, fields: [
  { name: 'region', type: 'text' as const, role: 'breakdown' as const, filled: 4, records: 4, values: ['North', 'South'] },
  { name: 'sales', type: 'number' as const, role: 'analysed' as const, filled: 4, records: 4 },
] }

function groupsByRegion() {
  vi.mocked(api.tableFields).mockResolvedValue(REGIONS)
  vi.mocked(api.queryTable).mockImplementation(async (_id, spec) => ({
    groups: spec.group_by?.length ? [
      { keys: ['North'], values: [30, 2], records: 2 },
      { keys: ['South'], values: [10, 2], records: 2 },
    ] : [], group_by: [], measures: [], group_count: 2, truncated: false, records: 4, matched_records: 4,
  }))
}

it.each(['en', 'ar'] as const)('a click on a bar keeps that group alone in the address, and a second click releases it (%s)', async (locale) => {
  applyLocale(locale)
  groupsByRegion()
  const user = userEvent.setup()
  const onNavigate = vi.fn()
  const view = render(<DashboardView runId="r1" page="breakdown" query="" onNavigate={onNavigate} onOpenRun={vi.fn()} />)
  const keep = locale === 'ar' ? 'إبقاء North فقط' : 'Keep only North'
  const bar = await screen.findByRole('button', { name: keep })
  expect(bar).toHaveAttribute('aria-pressed', 'false')
  await user.click(bar)
  expect(onNavigate).toHaveBeenLastCalledWith({ tab: 'dashboard', runId: 'r1', page: 'breakdown', query: 'f.region=North' })
  view.unmount()
  render(<DashboardView runId="r1" page="breakdown" query="f.region=North" onNavigate={onNavigate} onOpenRun={vi.fn()} />)
  const release = locale === 'ar' ? 'إظهار كل المجموعات مجدداً (North)' : 'Show every group again (North)'
  const held = await screen.findByRole('button', { name: release })
  expect(held).toHaveAttribute('aria-pressed', 'true')
  await user.click(held)
  expect(onNavigate).toHaveBeenLastCalledWith({ tab: 'dashboard', runId: 'r1', page: 'breakdown', query: undefined })
})

it('a saved view is applied once when the dashboard opens without an address of its own', async () => {
  groupsByRegion()
  vi.mocked(api.getDashboardView).mockResolvedValue({ view: { page: 'trend', query: 'f.region=South', run_id: 'r0', updated_at: '' } })
  const onNavigate = vi.fn()
  render(<DashboardView runId="r1" page={null} query="" onNavigate={onNavigate} onOpenRun={vi.fn()} />)
  await screen.findByText('Saved view applied.')
  expect(onNavigate).toHaveBeenCalledWith({ tab: 'dashboard', runId: 'r1', page: 'trend', query: 'f.region=South' })
  expect(onNavigate).toHaveBeenCalledTimes(1)
})

it('saving and forgetting a view go to the server and are confirmed', async () => {
  groupsByRegion()
  vi.mocked(api.saveDashboardView).mockResolvedValue({ view: { page: 'breakdown', query: 'f.region=North', run_id: 'r1', updated_at: '' } })
  vi.mocked(api.forgetDashboardView).mockResolvedValue(undefined)
  const user = userEvent.setup()
  render(<DashboardView runId="r1" page="breakdown" query="f.region=North" onNavigate={vi.fn()} onOpenRun={vi.fn()} />)
  await user.click(await screen.findByRole('button', { name: 'Save this view' }))
  expect(api.saveDashboardView).toHaveBeenCalledWith('r1', { page: 'breakdown', query: 'f.region=North' }, 'en')
  await screen.findByText('View saved. Every analysis of this dataset opens this way.')
  await user.click(screen.getByRole('button', { name: 'Forget the saved view' }))
  expect(api.forgetDashboardView).toHaveBeenCalledWith('r1')
  await screen.findByText('Saved view forgotten.')
  expect(screen.queryByRole('button', { name: 'Forget the saved view' })).not.toBeInTheDocument()
})
