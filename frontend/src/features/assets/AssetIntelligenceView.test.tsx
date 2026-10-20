import { act, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api } from '../../shared/api'
import type { RunKpis } from '../../shared/types'
import { runFixture } from '../../tests/run-fixture'
import { AssetIntelligenceView } from './AssetIntelligenceView'

const railway = (id: string) => runFixture({
  id, dataset_name: `${id}.csv`, state: 'awaiting_approval',
  tasks: [{ id: 'rail', role: 'rail_asset_manager', title: 'Rail', state: 'succeeded', summary: 'Synthetic railway evidence', quality_checks: [], claims: [] }],
})
const measures = (run: string, title: string): RunKpis => ({
  run, language: 'en', records: 1, unavailable: {}, measures: [{
    key: 'cost', title, value: 13, scale: 'money', numerator: 13, denominator: 1,
    formula: 'sum(cost) / count', population: 'Synthetic observations', records: 1,
    records_excluded: 0, records_unmeasured: 0, missing_policy: '', undefined_reason: null, edge_cases: '',
  }],
})
function deferred<T>() {
  let resolve!: (value: T) => void
  return { promise: new Promise<T>((done) => { resolve = done }), resolve: (value: T) => resolve(value) }
}
beforeEach(() => {
  applyLocale('en')
  vi.spyOn(api, 'pipelines').mockResolvedValue({ profiles: { maintenance: ['rail_asset_manager'] }, stages: [], default: [], problems: [] })
})
afterEach(() => { vi.restoreAllMocks(); act(() => applyLocale('en')) })

it('finds railway evidence behind more than eight newer unrelated analyses', async () => {
  const old = railway('older-railway')
  const newer = Array.from({ length: 10 }, (_, index) => runFixture({ id: `generic-${index}`, updated_at: '2026-10-20T00:00:00Z' }))
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [...newer, old] })
  vi.spyOn(api, 'getRun').mockImplementation(async (id) => id === old.id ? old : newer.find((run) => run.id === id)!)
  vi.spyOn(api, 'runKpis').mockResolvedValue(measures(old.id, 'Older railway measure'))
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  expect(await screen.findByText('older-railway.csv')).toBeVisible()
  expect(await screen.findByText(/Older railway measure/)).toBeVisible()
  expect(screen.queryByText('No validated railway asset analysis yet')).not.toBeInTheDocument()
  expect(api.getRun).toHaveBeenCalledTimes(11)
})

it('hides the previous run measurements while a different run KPI request is pending and translates states', async () => {
  const old = railway('old'), next = railway('new')
  const pending = deferred<RunKpis>()
  vi.spyOn(api, 'listRuns').mockResolvedValueOnce({ runs: [old] }).mockResolvedValue({ runs: [next] })
  vi.spyOn(api, 'getRun').mockImplementation(async (id) => id === old.id ? old : next)
  vi.spyOn(api, 'runKpis').mockImplementation((id) => id === old.id
    ? Promise.resolve(measures(old.id, 'Old measurement')) : pending.promise)
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  expect(await screen.findByText(/Old measurement/)).toBeVisible()
  act(() => applyLocale('ar'))
  expect(await screen.findByText('new.csv')).toBeVisible()
  await waitFor(() => expect(api.runKpis).toHaveBeenLastCalledWith('new', 'ar'))
  expect(screen.queryByText(/Old measurement/)).not.toBeInTheDocument()
  expect(screen.getByText('بانتظار الموافقة')).toBeVisible()
  expect(screen.getByText('نجح')).toBeVisible()
  await act(async () => pending.resolve(measures(next.id, 'New measurement')))
  expect(await screen.findByText(/New measurement/)).toBeVisible()
})

it('ignores a delayed KPI response from a previous run', async () => {
  const old = railway('old'), next = railway('new')
  const pending = deferred<RunKpis>()
  vi.spyOn(api, 'listRuns').mockResolvedValueOnce({ runs: [old] }).mockResolvedValue({ runs: [next] })
  vi.spyOn(api, 'getRun').mockImplementation(async (id) => id === old.id ? old : next)
  vi.spyOn(api, 'runKpis').mockImplementation((id) => id === old.id
    ? pending.promise : Promise.resolve(measures(next.id, 'Current measurement')))
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  await waitFor(() => expect(api.runKpis).toHaveBeenCalledWith('old', 'en'))
  act(() => applyLocale('ar'))
  expect(await screen.findByText(/Current measurement/)).toBeVisible()
  await act(async () => pending.resolve(measures(old.id, 'Late measurement')))
  expect(screen.getByText(/Current measurement/)).toBeVisible()
  expect(screen.queryByText(/Late measurement/)).not.toBeInTheDocument()
})
