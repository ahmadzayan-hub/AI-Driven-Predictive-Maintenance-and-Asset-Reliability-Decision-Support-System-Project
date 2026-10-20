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
  return { ...actual, api: { ...actual.api, listRuns: vi.fn(), tableFields: vi.fn(), getRun: vi.fn(), queryTable: vi.fn(), tableRecords: vi.fn() } }
})
beforeEach(() => {
  applyLocale('en')
  vi.clearAllMocks()
  vi.mocked(api.tableFields).mockResolvedValue({ records: 1, fields: [{ name: 'label', type: 'text', role: null, filled: 1, records: 1 }] })
  vi.mocked(api.getRun).mockRejectedValue(new ApiError('Not found', 404))
  vi.mocked(api.queryTable).mockResolvedValue({ groups: [], group_by: [], measures: [], group_count: 0, truncated: false, records: 1, matched_records: 1 })
  vi.mocked(api.tableRecords).mockResolvedValue({ columns: ['label'], rows: [['Owner A fixture']], total: 1 })
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
  expect(screen.getByRole('link', { name: 'Analyse maintenance data' })).toHaveAttribute('href', '#/runs?source=upload&profile=maintenance')
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
    groups: spec.group_by?.length ? Array.from({ length: 1000 }, (_, index) => ({ keys: [`period-${index}`], values: [1, 1, 1], records: 1 })) : [],
    group_by: [], measures: [], group_count: spec.group_by?.length ? 1001 : 1,
    truncated: Boolean(spec.group_by?.length), records: 1001, matched_records: 1001,
  }))
  for (const locale of ['en', 'ar'] as const) {
    applyLocale(locale)
    const view = render(<DashboardView runId="r1" page={page} query="" onNavigate={vi.fn()} onOpenRun={vi.fn()} />)
    const expected = dashMessages[locale]['dash.trendTruncated'].split('{shown}')[0]
    expect(await screen.findByText((content) => content.startsWith(expected) && content.includes('1,001'))).toBeVisible()
    view.unmount()
  }
}, 15000)
