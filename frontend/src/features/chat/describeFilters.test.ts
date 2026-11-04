import { expect, it } from 'vitest'
import { describeFilters } from './describeFilters'

it('says the filters as a reader would, and nothing when there are none', () => {
  expect(describeFilters([])).toBe('')
  expect(describeFilters(undefined)).toBe('')
  expect(describeFilters([{ column: 'Site', op: 'in', values: ['North'] }])).toBe('Site: North')
  expect(describeFilters([{ column: 'Site', op: 'in', values: ['North', 'South'] }, { column: 'Cost', op: 'gte', value: 100 }]))
    .toBe('Site: North, South · Cost ≥ 100')
})
