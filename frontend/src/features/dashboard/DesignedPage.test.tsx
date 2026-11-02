import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { api } from '../../shared/api'
import type { LayoutResult, LayoutSection, QueryAnswer } from '../../shared/types'
import { DesignedPage } from './DesignedPage'
import { addVersion, readHistory, restore, togglePin, MAX_VERSIONS } from './layoutHistory'
import { EMPTY, type Roles } from './state'

// Synthetic layouts and answers. The planner is the server's; nothing here is a real model.
const t = (en: string) => ({ en, ar: en })
const kpi: LayoutSection = { id: 'records', component: 'kpi', title: t('Records'), purpose: t('How many.'), span: 1,
  interactions: ['filter'], binding: { measures: [{ agg: 'count' }] } }
const rank: LayoutSection = { id: 'ranking', component: 'ranking', title: t('Cost by class'), purpose: t('Largest first.'),
  span: 2, interactions: ['filter'], binding: { group_by: ['Class'], measures: [{ agg: 'sum', column: 'Cost' }] } }
const gap: LayoutSection = { id: 'gap-forecast', component: 'gap', title: t('Not available yet'), purpose: t('Missing.'),
  span: 1, interactions: [], binding: { measures: [], capability: 'forecast' }, reason: { en: 'No validated forecast result is attached to this run.', ar: 'لا توجد نتيجة تنبؤ.' } }
const result = (sections: LayoutSection[], fingerprint = 'fp1', source: 'model' | 'rules' = 'rules'): LayoutResult => ({
  plan: { version: 1, objective: '', sections }, source, provider: source === 'model' ? 'ollama qwen2.5:3b' : null,
  notes: [source === 'rules' ? { en: 'No language model is configured.', ar: 'لا يوجد نموذج.' } : { en: 'Planned by ollama qwen2.5:3b', ar: 'صمّمه ollama qwen2.5:3b' }],
  problems: [], capabilities: {}, fingerprint })
const answer = (groups: Array<[string | null, number]>): QueryAnswer => ({ group_by: [], measures: [], groups: groups.map(([k, v]) => ({ keys: [k], records: 1, values: [v] })),
  group_count: groups.length, truncated: false, matched_records: 42, records: 42 })
const roles: Roles = { measure: 'Cost', breakdown: 'Class', date: null, measures: ['Cost'], texts: [] }

beforeEach(() => { localStorage.clear() })
afterEach(() => { vi.restoreAllMocks() })

it('keeps up to five versions, carries pins on the same schema and drops them on a new one', () => {
  let h = addVersion(null, result([kpi, rank]), '2026-11-03T08:00:00Z')
  h = togglePin(h, 'ranking')
  h = addVersion(h, result([kpi, gap]), '2026-11-03T08:01:00Z')
  expect(h.versions[h.current].result.plan.sections.map((s) => s.id)).toEqual(['ranking', 'records', 'gap-forecast'])
  for (let i = 0; i < 6; i++) h = addVersion(h, result([kpi]), `2026-11-03T09:0${i}:00Z`)
  expect(h.versions).toHaveLength(MAX_VERSIONS)
  expect(restore(h, 0).current).toBe(0)
  const fresh = addVersion(h, result([kpi], 'fp2'), '2026-11-03T10:00:00Z')
  expect(fresh.versions).toHaveLength(1)
  expect(fresh.pinned).toEqual([])
})

it('designs once, then a refresh keeps the layout without asking again', async () => {
  const plan = vi.spyOn(api, 'planLayout').mockResolvedValue(result([kpi, rank, gap]))
  vi.spyOn(api, 'queryTable').mockResolvedValue(answer([['Pumps', 900], ['Doors', 300]]))
  const view = render(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  expect(await screen.findByRole('region', { name: 'Cost by class' })).toBeInTheDocument()
  expect(screen.getByText(/No validated forecast result/)).toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('Rule-based design')
  view.unmount()
  render(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  expect(await screen.findByRole('region', { name: 'Records' })).toBeInTheDocument()
  expect(plan).toHaveBeenCalledTimes(1)
})

it('applies the shared filters to every section and a pick narrows the dashboard state', async () => {
  vi.spyOn(api, 'planLayout').mockResolvedValue(result([kpi, rank]))
  const query = vi.spyOn(api, 'queryTable').mockResolvedValue(answer([['Pumps', 900], ['Doors', 300]]))
  const setState = vi.fn()
  const filters = [{ column: 'Region', op: 'in' as const, values: ['North'] }]
  render(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={filters} setState={setState} />)
  await screen.findByRole('region', { name: 'Cost by class' })
  await waitFor(() => expect(query).toHaveBeenCalledTimes(2))
  for (const [, spec] of query.mock.calls) expect(spec.filters).toEqual(filters)
  fireEvent.click(await screen.findByRole('button', { name: /Pumps/ }))
  expect(setState).toHaveBeenCalledWith(expect.objectContaining({ filters: { Class: ['Pumps'] } }))
})

it('pins a section and restores an earlier layout', async () => {
  vi.spyOn(api, 'planLayout').mockResolvedValueOnce(result([kpi, rank])).mockResolvedValueOnce(result([kpi], 'fp1', 'model'))
  vi.spyOn(api, 'queryTable').mockResolvedValue(answer([['Pumps', 900]]))
  render(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  const ranking = await screen.findByRole('region', { name: 'Cost by class' })
  fireEvent.click(ranking.querySelector('.layout__pin')!)
  expect(readHistory('r1')!.pinned).toEqual(['ranking'])
  fireEvent.click(screen.getByRole('button', { name: 'Redesign' }))
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Designed by ollama qwen2.5:3b'))
  expect(screen.getByRole('region', { name: 'Cost by class' })).toBeInTheDocument()  // pinned, carried over
  fireEvent.click(screen.getByText('Earlier layouts'))
  fireEvent.click(screen.getAllByRole('button', { name: /Version 1/ })[0])
  expect(readHistory('r1')!.current).toBe(0)
})

it('keeps the last valid layout when designing fails, and drops a late answer for another run', async () => {
  let release!: (value: LayoutResult) => void
  vi.spyOn(api, 'planLayout').mockResolvedValueOnce(result([kpi])).mockRejectedValueOnce(new Error('down'))
    .mockImplementationOnce(() => new Promise((resolve) => { release = resolve }))
  vi.spyOn(api, 'queryTable').mockResolvedValue(answer([[null, 7]]))
  const view = render(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  await screen.findByRole('region', { name: 'Records' })
  fireEvent.click(screen.getByRole('button', { name: 'Redesign' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('last valid layout is kept')
  expect(screen.getByRole('region', { name: 'Records' })).toBeInTheDocument()
  view.rerender(<DesignedPage runId="r2" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  view.rerender(<DesignedPage runId="r1" roles={roles} state={EMPTY} filters={[]} setState={vi.fn()} />)
  release(result([rank], 'fp-late'))
  await new Promise((r) => setTimeout(r, 0))
  expect(readHistory('r2')).toBeNull()
})
