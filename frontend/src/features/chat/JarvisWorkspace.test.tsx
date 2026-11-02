import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { JarvisWorkspace, jarvisApi, type JarvisAnswer } from './JarvisWorkspace'
import type { SessionState } from '../../shared/types'
import { applyLocale } from '../../i18n'
import { dataChatMessages } from './dataChatMessages'
import { jarvisSpeech } from './jarvisSpeech'
const context = { run_id: 'synthetic', dataset_id: 'd1', dataset_name: 'SYNTHETIC.csv', source_sha256: 'a'.repeat(64), analysis_revision: 'b'.repeat(64), filters: [], records: 3, total_records: 3 }
const session: SessionState = { session_id: 's1', agent_name: 'Miyaar', version: 'test', welcome: '', ended: false, created_at: '', transcript: [], preferences: {}, memory: {}, memory_entries: [], history: [], memory_persisted: false, commands: [], data_context: context,
  data_chat_labels: Object.fromEntries(Object.entries(dataChatMessages.en).map(([k,v]) => [k.replace('dataChat.', ''), v])) as SessionState['data_chat_labels'] }
const result: JarvisAnswer = { text: '500 · https://example.invalid/ref · ops@example.invalid · SYN-01', source: 'rules', result: { ...context, currency: null, provenance: 'deterministic_kpi_register', llm_explanation: null, measures: [{ key: 'maintenance_cost', title: 'Maintenance cost', value: 500, formula: 'sum(Maintenance_Cost_USD)' }] } }
beforeEach(() => { vi.restoreAllMocks(); applyLocale('en') })
function question() { fireEvent.change(screen.getByRole('textbox'), { target: { value: 'What is total maintenance cost?' } }) }
it('preserves evidence, separates speech and confirms only an explicit local review', async () => {
  vi.spyOn(jarvisApi, 'query').mockResolvedValue(result)
  render(<JarvisWorkspace session={session} />); question()
  fireEvent.click(screen.getByRole('button', { name: 'Calculate from selected report' }))
  await screen.findByText(result.text)
  expect(screen.getByText(/Maintenance cost: 500 unit not declared/)).toHaveTextContent('Measurement coverage is unavailable')
  expect(jarvisApi.query).toHaveBeenCalledWith('s1', 'What is total maintenance cost?', context, 'en', expect.any(AbortSignal))
  expect(screen.getByRole('button', { name: 'Confirm local review' })).toBeDisabled()
  fireEvent.click(screen.getByRole('checkbox'))
  fireEvent.click(screen.getByRole('button', { name: 'Confirm local review' }))
  expect(screen.getByText(/Review confirmed for this answer/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'What is availability?' }))
  expect(screen.queryByText(result.text)).not.toBeInTheDocument()
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})
it('deduplicates active requests and ignores late replies after interrupt', async () => {
  let resolve!: (value: JarvisAnswer) => void
  const call = vi.spyOn(jarvisApi, 'query').mockReturnValue(new Promise(r => { resolve = r }))
  render(<JarvisWorkspace session={session} />); question()
  const ask = screen.getByRole('button', { name: 'Calculate from selected report' })
  fireEvent.click(ask); fireEvent.click(ask); expect(call).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: 'Stop / interrupt' }))
  expect(call.mock.calls[0][4].aborted).toBe(true)
  await act(async () => resolve(result))
  expect(screen.queryByText(result.text)).not.toBeInTheDocument()
})
it('invalidates answer on dataset changes and suppresses errors from superseded requests', async () => {
  let reject!: (reason: Error) => void
  vi.spyOn(jarvisApi, 'query').mockReturnValue(new Promise((_,r) => { reject = r }))
  const view = render(<JarvisWorkspace session={session} />); question()
  fireEvent.click(screen.getByRole('button', { name: 'Calculate from selected report' }))
  view.rerender(<JarvisWorkspace session={{ ...session, data_context: { ...context, dataset_name: 'NEW.csv', analysis_revision: 'c'.repeat(64) } }} />)
  await act(async () => reject(new Error('old failure')))
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  expect(screen.getByRole('textbox')).toHaveValue('')
})
it('shows unavailable service without making up output', async () => {
  vi.spyOn(jarvisApi, 'query').mockRejectedValue(new Error('offline'))
  render(<JarvisWorkspace session={session} />); question()
  fireEvent.click(screen.getByRole('button', { name: 'Calculate from selected report' }))
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('No answer was confirmed'))
  expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
})
it('renders Arabic RTL with text fallback and requires selection', () => {
  applyLocale('ar')
  render(<JarvisWorkspace session={{ ...session, data_context: null }} />)
  expect(document.documentElement.dir).toBe('rtl')
  expect(screen.getByRole('button', { name: 'احسب من التقرير المحدد' })).toBeDisabled()
  expect(screen.getByRole('textbox')).toBeEnabled()
  expect(screen.getByText('اختر تقريراً مكتملاً للبدء.')).toBeInTheDocument()
})

it('keeps units, currency uncertainty and coverage in both spoken summaries', () => {
  const answer: JarvisAnswer = { ...result, result: { ...result.result!, measures: [
    { key: 'mtbf', title: 'MTBF', value: 20, scale: 'hours', records: 2, records_unmeasured: 1 },
    { key: 'asset_age_summary', title: 'Age', value: 10, scale: 'years', records: 3, records_unmeasured: 0 },
    { key: 'maintenance_cost', title: 'Cost', value: 500, scale: 'money', records: 3, records_unmeasured: 0 },
    { key: 'availability', title: 'Availability', value: null, scale: 'percent', records: 0, records_unmeasured: 3 },
    { key: 'mttr', title: 'MTTR', value: null, reason: 'Required columns are missing.' },
  ] } }
  const english = jarvisSpeech(answer, 'en')
  for (const text of ['20 hours', '10 years', '500 currency not declared', 'Measured records: 2; unmeasured: 1', 'this is not zero', 'Required columns are missing.']) expect(english).toContain(text)
  const arabic = jarvisSpeech(answer, 'ar')
  for (const text of ['20 ساعة', '10 سنوات', '500 العملة غير محددة', 'غير المقاسة: 1', 'ليست قيمة صفرية']) expect(arabic).toContain(text)
  expect(jarvisSpeech({ ...answer, result: { ...answer.result!, currency: 'AED' } }, 'en')).toContain('500 AED')
  expect(answer.text).toBe(result.text)
})
