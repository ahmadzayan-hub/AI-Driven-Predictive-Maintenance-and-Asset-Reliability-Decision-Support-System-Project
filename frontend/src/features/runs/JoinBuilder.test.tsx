import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import { api } from '../../shared/api'
import type { DatasetDetail, DatasetSummary, JoinPreview, JoinSpec } from '../../shared/types'
import { JoinBuilder } from './JoinBuilder'

// Loose join keys (docs/adr/2026-10-30-loose-join-keys.md): a join can ignore
// letter case, spaces and separators in its keys, and the preview says how many more rows
// that would match.
const datasets = [
  { id: 'd1', name: 'sales.csv' },
  { id: 'd2', name: 'products.csv' },
] as DatasetSummary[]
const join: JoinSpec = { dataset_id: 'd2', keys: [{ left: 'product', right: 'code' }], how: 'left' }

beforeEach(() => {
  applyLocale('en')
  vi.spyOn(api, 'getDataset').mockImplementation(async (id: string) => ({
    columns: (id === 'd1' ? ['product', 'revenue'] : ['code', 'category']).map((name) => ({ name })),
  }) as unknown as DatasetDetail)
})
afterEach(() => vi.restoreAllMocks())

it('declares a loose join when the box is ticked and clears it when unticked', async () => {
  const user = userEvent.setup()
  const onChange = vi.fn()
  const { rerender } = render(<JoinBuilder primaryId="d1" datasets={datasets} disabled={false}
    joins={[join]} breakdown="" onChange={onChange} />)
  await user.click(screen.getByRole('checkbox', { name: 'Ignore letter case, spaces and separators in keys' }))
  expect(onChange).toHaveBeenLastCalledWith([{ ...join, match: 'loose' }], '')
  rerender(<JoinBuilder primaryId="d1" datasets={datasets} disabled={false}
    joins={[{ ...join, match: 'loose' }]} breakdown="" onChange={onChange} />)
  await user.click(screen.getByRole('checkbox', { name: 'Ignore letter case, spaces and separators in keys' }))
  expect(onChange.mock.lastCall?.[0][0].match).toBeUndefined()
})

it('offers no such box for a stack, which has no key', () => {
  render(<JoinBuilder primaryId="d1" datasets={datasets} disabled={false}
    joins={[{ dataset_id: 'd2', keys: [], how: 'stack' }]} breakdown="" onChange={vi.fn()} />)
  expect(screen.queryByRole('checkbox', { name: 'Ignore letter case, spaces and separators in keys' })).toBeNull()
})

it.each(['en', 'ar'] as const)('says how many more rows a loose join would match (%s)', async (locale) => {
  applyLocale(locale)
  const user = userEvent.setup()
  const preview = {
    rows_before: 24, rows_after: 24, columns: [], added_columns: ['category'], breakdown_choices: [],
    personal_data: [], preview: [],
    joins: [{ dataset_id: 'd2', name: 'products.csv', alias: 'products', how: 'left', keys: join.keys,
      rows_in: 24, rows_out: 24, matched: 6, unmatched: 18, coverage: 0.25, unmatched_keys: ['P1'],
      lookup_rows: 4, lookup_unused: 0, added_columns: ['category'], renamed: {}, near_matches: 12 }],
  } as unknown as JoinPreview
  vi.spyOn(api, 'previewJoins').mockResolvedValue(preview)
  render(<JoinBuilder primaryId="d1" datasets={datasets} disabled={false}
    joins={[join]} breakdown="" onChange={vi.fn()} />)
  await user.click(screen.getByRole('button', { name: locale === 'ar' ? 'معاينة الدمج' : 'Preview the merge' }))
  expect(await screen.findByText(locale === 'ar'
    ? /وسيتطابق 12 صفاً آخر عند تجاهل حالة الأحرف والمسافات/
    : /12 more would match ignoring case, spaces and separators/)).toBeInTheDocument()
})

it.each(['en', 'ar'] as const)('turns a named typing slip into a correction only when pressed (%s)', async (locale) => {
  applyLocale(locale)
  const user = userEvent.setup()
  const onChange = vi.fn()
  vi.spyOn(api, 'previewJoins').mockResolvedValue({
    rows_before: 12, rows_after: 12, columns: [], added_columns: ['category'], breakdown_choices: [],
    personal_data: [], preview: [],
    joins: [{ dataset_id: 'd2', name: 'products.csv', alias: 'products', how: 'left', keys: join.keys,
      rows_in: 12, rows_out: 12, matched: 6, unmatched: 6, coverage: 0.5, unmatched_keys: ['PMP-03'],
      lookup_rows: 2, lookup_unused: 1, added_columns: ['category'], renamed: {},
      typo_examples: [{ key: 'PMP-03', candidate: 'PUMP-03' }] }],
  } as unknown as JoinPreview)
  render(<JoinBuilder primaryId="d1" datasets={datasets} disabled={false} joins={[join]} breakdown="" onChange={onChange} />)
  await user.click(screen.getByRole('button', { name: locale === 'ar' ? 'معاينة الدمج' : 'Preview the merge' }))
  const fix = await screen.findByRole('button', { name: locale === 'ar' ? 'اقرأ PMP-03 على أنه PUMP-03' : 'Read PMP-03 as PUMP-03' })
  expect(onChange).not.toHaveBeenCalled()
  await user.click(fix)
  expect(onChange).toHaveBeenLastCalledWith([{ ...join, corrections: [{ from: 'PMP-03', to: 'PUMP-03' }] }], '')
})
