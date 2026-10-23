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

it('reads the one server answer for the evidence and never the run list (U10)', async () => {
  const old = railway('older-railway')
  vi.spyOn(api, 'assetEvidence').mockResolvedValue({ run: old, scanned: 11, capped: false })
  const list = vi.spyOn(api, 'listRuns')
  const detail = vi.spyOn(api, 'getRun')
  vi.spyOn(api, 'runKpis').mockResolvedValue(measures(old.id, 'Older railway measure'))
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  expect(await screen.findByText('older-railway.csv')).toBeVisible()
  expect(await screen.findByText(/Older railway measure/)).toBeVisible()
  expect(screen.queryByText('No validated railway asset analysis yet')).not.toBeInTheDocument()
  expect(api.assetEvidence).toHaveBeenCalledTimes(1)
  expect(list).not.toHaveBeenCalled()
  expect(detail).not.toHaveBeenCalled()
  // The figures say when their run was last updated (U16).
  expect(screen.getByText('As of')).toBeVisible()
})

it('says the scan was capped when the server says so', async () => {
  vi.spyOn(api, 'assetEvidence').mockResolvedValue({ run: null, scanned: 50, capped: true })
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  expect(await screen.findByText('No validated railway asset analysis yet')).toBeVisible()
  expect(screen.getByText(/most recent/i)).toBeVisible()
})

it('hides the previous run measurements while a different run KPI request is pending and translates states', async () => {
  const old = railway('old'), next = railway('new')
  const pending = deferred<RunKpis>()
  vi.spyOn(api, 'assetEvidence').mockResolvedValueOnce({ run: old, scanned: 1, capped: false })
    .mockResolvedValue({ run: next, scanned: 1, capped: false })
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
  vi.spyOn(api, 'assetEvidence').mockResolvedValueOnce({ run: old, scanned: 1, capped: false })
    .mockResolvedValue({ run: next, scanned: 1, capped: false })
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

it('shows measures as family tiles, keeps a verdict reason on its tile and says "no target" once, folded', async () => {
  const run = railway('tiles')
  const base = measures(run.id, 'unused').measures[0]
  vi.spyOn(api, 'assetEvidence').mockResolvedValue({ run, scanned: 1, capped: false })
  vi.spyOn(api, 'runKpis').mockResolvedValue({ ...measures(run.id, 'unused'), measures: [
    { ...base, key: 'availability', title: 'Availability', scale: 'percent', value: 97.5, family: 'reliability', population_label: 'Every observation',
      assessment: { status: 'unassessed', reason: 'No display target is configured.', reason_code: 'no_target', direction: null, source_ref: null, rule_id: null, thresholds: null } },
    { ...base, key: 'loss', title: 'Loss per downtime hour', family: 'cost',
      assessment: { status: 'bad', reason: 'Above the fictional ceiling.', reason_code: 'above', direction: 'lower', source_ref: 'Fictional QA', rule_id: 'r1', thresholds: { good_at: 5, okay_at: 10 } } },
  ] })
  render(<AssetIntelligenceView onUpload={vi.fn()} onOpenRun={vi.fn()} />)
  const availability = (await screen.findByText('Availability')).closest('li')!
  const loss = screen.getByText('Loss per downtime hour').closest('li')!
  expect(availability).toHaveAttribute('data-family', 'reliability')
  // The reader-language label is shown; the code is the fallback.
  expect(availability).toHaveTextContent('Every observation')
  expect(loss).toHaveTextContent('Synthetic observations')
  expect(loss).toHaveAttribute('data-family', 'cost')
  expect(loss).toHaveTextContent('Above the fictional ceiling.')
  expect(availability).not.toHaveTextContent('No display target')
  const note = screen.getByText(/have no display target yet/)
  expect(note.closest('details')).not.toHaveAttribute('open')
  expect(note).not.toBeVisible()
  // Figures come before the screening note that qualifies the run.
  const screening = screen.getByText('Engineering review screening')
  expect(availability.compareDocumentPosition(screening) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
})
