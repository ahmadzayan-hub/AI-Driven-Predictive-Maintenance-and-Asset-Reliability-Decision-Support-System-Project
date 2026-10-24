import { describe, expect, it } from 'vitest'
import { hasWorkSource } from '../shared/sourceHandoff'
import { parseRoute, routeHash } from '../app/routing'
import { drill, EMPTY, filterCount, pagesFor, readState, rolesOf, toFilters, writeState } from '../features/dashboard/state'
import type { TableField } from '../shared/types'

const FIELDS: TableField[] = [
  { name: 'month', type: 'text', role: 'date', filled: 4, records: 4, values: ['2025-01', '2025-02'] },
  { name: 'region', type: 'text', role: 'breakdown', filled: 4, records: 4, values: ['North', 'South'] },
  { name: 'note', type: 'text', role: null, filled: 4, records: 4, distinct: 900 },
  { name: 'revenue', type: 'number', role: 'analysed', filled: 4, records: 4, min: 1, max: 9 },
  { name: 'units', type: 'number', role: 'measure', filled: 4, records: 4, min: 1, max: 3 },
]

describe('dashboard addresses (ADR 0032)', () => {
  it('carries only a validated source run ID to operations, never filters or approval', () => {
    expect(parseRoute(routeHash({ tab: 'operations', runId: 'run_7' }))).toEqual({ tab: 'operations', runId: 'run_7' })
    expect(parseRoute('#/operations/../bad')).toEqual({ tab: 'operations' })
    expect(parseRoute('#/operations/run_7?approved=true&asset=other')).toEqual({ tab: 'operations', runId: 'run_7' })
  })
  it('requires explicit dataset identity and an eligible draft state', () => {
    for (const dataset_id of [null, undefined, '', ' ']) expect(hasWorkSource({ state: 'completed', dataset_id })).toBe(false)
    for (const state of ['queued', 'running', 'failed', 'cancelled'] as const) expect(hasWorkSource({ state, dataset_id: 'd1' })).toBe(false)
    for (const state of ['awaiting_approval', 'completed'] as const) expect(hasWorkSource({ state, dataset_id: 'd1' })).toBe(true)
  })

  it('selects only known upload profiles and keeps existing runs unchanged', () => {
    const route = { tab: 'runs' as const, source: 'upload' as const, profile: 'maintenance' as const }
    expect(parseRoute(routeHash(route))).toEqual(route)
    expect(parseRoute('#/runs?source=upload&profile=untrusted')).toEqual({ tab: 'runs', source: 'upload' })
    expect(parseRoute('#/runs/r1?source=upload&profile=maintenance')).toEqual({ tab: 'runs', runId: 'r1' })
  })
  it('links directly to a real upload form without replacing an existing run', () => {
    expect(parseRoute('#/runs?source=upload')).toEqual({ tab: 'runs', source: 'upload' })
    expect(routeHash({ tab: 'runs', source: 'upload' })).toBe('#/runs?source=upload')
    expect(parseRoute('#/runs/r1?source=upload')).toEqual({ tab: 'runs', runId: 'r1' })
    expect(parseRoute('#/runs?source=invalid')).toEqual({ tab: 'runs' })
  })
  it('carry the run, the page and every choice, and survive a round trip', () => {
    const state = {
      ...EMPTY,
      filters: { region: ['North', 'South & West'] },
      from: '2025-01', to: '2025-06', by: 'channel', per: true, sort: 'revenue', desc: true, offset: 25,
    }
    const query = writeState(state)
    const route = parseRoute(routeHash({ tab: 'dashboard', runId: 'r1', page: 'breakdown', query }))
    expect(route).toEqual({ tab: 'dashboard', runId: 'r1', page: 'breakdown', query })
    expect(readState(route.query!)).toEqual(state)
  })

  it('refuse an id or a page that is not one', () => {
    expect(parseRoute('#/dashboard/../x/overview')).toEqual({ tab: 'dashboard' })
    expect(parseRoute('#/dashboard/r1/Over-view?f.a=1')).toEqual({ tab: 'dashboard', runId: 'r1', query: 'f.a=1' })
    expect(routeHash({ tab: 'dashboard' })).toBe('#/dashboard')
    expect(parseRoute('#/runs/r1')).toEqual({ tab: 'runs', runId: 'r1' })
  })

  it('leave defaults out of the address', () => {
    expect(writeState(EMPTY)).toBe('')
    expect(readState('o=-3&per=yes&lo=abc').offset).toBe(0)
  })
})

describe('dashboard filters', () => {
  it('apply to every query as named filters', () => {
    const state = { ...readState('f.region=North&from=2025-02&lo=2&hi=5&hiop=lt') }
    expect(toFilters(state, 'month', 'revenue')).toEqual([
      { column: 'region', op: 'in', values: ['North'] },
      { column: 'month', op: 'gte', value: '2025-02' },
      { column: 'revenue', op: 'gte', value: 2 },
      { column: 'revenue', op: 'lt', value: 5 },
    ])
    expect(filterCount(state)).toBe(3)
  })

  it('drill a group down to its records, and a period to its range', () => {
    const byRegion = drill({ ...EMPTY, offset: 50 }, 'region', 'South', 'month')
    expect(byRegion.filters).toEqual({ region: ['South'] })
    expect(byRegion.offset).toBe(0)
    const byMonth = drill(EMPTY, 'month', '2025-02', 'month')
    expect([byMonth.from, byMonth.to]).toEqual(['2025-02', '2025-02'])
  })
})

describe('dashboard pages follow the table', () => {
  it('reads the run’s own roles', () => {
    const roles = rolesOf(FIELDS)
    expect(roles).toMatchObject({ measure: 'revenue', breakdown: 'region', date: 'month', measures: ['revenue', 'units'] })
    expect(roles.texts.map((f) => f.name)).toEqual(['region', 'note'])
    expect(pagesFor(roles)).toEqual(['overview', 'breakdown', 'trend', 'distribution', 'relationship', 'records'])
  })

  it('has no trend without a date and no relationship with one measure', () => {
    const roles = rolesOf(FIELDS.filter((f) => f.name !== 'month' && f.name !== 'units'))
    expect(pagesFor(roles)).toEqual(['overview', 'breakdown', 'distribution', 'records'])
  })
})

describe('landing (the 22 October decision)', () => {
  it('opens on the Command Centre when the address names no view', () => {
    expect(parseRoute('')).toEqual({ tab: 'overview' })
    expect(parseRoute('#')).toEqual({ tab: 'overview' })
    expect(parseRoute('#/')).toEqual({ tab: 'overview' })
    expect(parseRoute('#/nowhere')).toEqual({ tab: 'overview' })
    expect(routeHash({ tab: 'overview' })).toBe('#/overview')
  })
  it('keeps every explicit address, including the assistant', () => {
    expect(parseRoute('#/assistant')).toEqual({ tab: 'chat' })
    expect(parseRoute('#/workspace')).toEqual({ tab: 'chat' })
    expect(parseRoute('#/approvals')).toEqual({ tab: 'approvals' })
    expect(parseRoute('#/dashboard')).toEqual({ tab: 'dashboard' })
    expect(routeHash({ tab: 'chat' })).toBe('#/assistant')
  })
})
