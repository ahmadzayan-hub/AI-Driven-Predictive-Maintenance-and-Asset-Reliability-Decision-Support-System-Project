import { Activity } from 'react'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { applyLocale } from '../i18n'
import { SourceInspector } from '../features/rmd/SourcePanel'
import { RecordsDialog } from '../features/rmd/EvidencePanel'
import { RmdAssistantPanel } from '../features/rmd/RmdAssistantPanel'
import { RmdView } from '../features/rmd/RmdView'
import type { EvidenceAnalysis, EvidencePack, EvidenceSource, SheetMapping } from '../features/rmd/types'

// Synthetic transport fixtures only. These names, identifiers and values do
// not represent an RMD source, procedure, incident or measured performance.
const actor = vi.hoisted(() => ({ subject: 'synthetic-owner' }))
vi.mock('../app/store', () => ({ useStore: () => ({ identity: { mode: 'jwt', principal: {
  subject: actor.subject, role: 'analyst', provider: 'test', email: '', permissions: ['read', 'write'],
} } }) }))

function response(body: unknown, status = 200): Response {
  return { ok: status < 400, status, json: async () => body } as Response
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}
function serve(handler: (url: URL, init: RequestInit) => Response | Promise<Response>) {
  const fetchMock = vi.fn((url: string, init: RequestInit = {}) => Promise.resolve(handler(new URL(url, 'https://synthetic.invalid'), init)))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

const source: EvidenceSource = {
  id: 'source-synthetic', name: 'synthetic-records.xlsx', kind: 'workbook', sha256: 'a'.repeat(64), revision: 3,
  sheets: [{ name: 'Synthetic records', header_row_proposed: 2, suggested_role: 'mms_work_order', source_row_count: 3,
    columns: [{ letter: 'A', label: 'SR' }, { letter: 'B', label: 'Work Group' }, { letter: 'C', label: 'Work Group', hidden: true }],
    rows: [{ source_row: 2, cells: { A: { value: 'SR' }, B: { value: 'Work Group' }, C: { value: 'Work Group' } } },
      { source_row: 3, cells: { A: { value: 'SYN-SR-1' }, B: { value: 'Synthetic junction' }, C: { value: 'Synthetic category' } } }],
  }],
  mapping: { sheets: [{ name: 'Synthetic records', role: 'mms_work_order', header_row: 2, columns: { sr_id: 'A', location: 'B' }, date_format: 'ISO' }] },
}
const analysis: EvidenceAnalysis = {
  id: 'analysis-synthetic', calculated_at: '2026-01-01T00:00:00Z', calculation_version: 'synthetic-v1', language: 'en',
  counts_by_grain: { mms_work_order: 1 }, kpis: [], charts: [], priorities: [], conflicts: [], proposed_links: [],
  completeness: [], readiness: [], limitations: ['Synthetic fixture; no operational conclusions.'],
}
const pack: EvidencePack = {
  id: 'pack-synthetic', title: 'Synthetic evidence pack', created_at: '2026-01-01T00:00:00Z',
  sources: [source], analyses: [{ id: analysis.id, created_at: analysis.calculated_at }], permissions: { write: true },
}

beforeEach(() => {
  applyLocale('en'); actor.subject = 'synthetic-owner'; localStorage.clear()
  localStorage.setItem('aos-token', 'synthetic-test-token')
})
afterEach(() => { act(() => applyLocale('en')); vi.unstubAllGlobals(); vi.restoreAllMocks(); localStorage.clear() })

describe('RMD mapping confirmation', () => {
  it('keeps duplicate headings separate and retains a refused draft for an explicit retry', async () => {
    const user = userEvent.setup(), changed = vi.fn(), writes: { sheets: SheetMapping[]; expected_revision: number }[] = []
    serve((url, init) => {
      if (init.method === 'PUT') {
        const body = JSON.parse(String(init.body)) as { sheets: SheetMapping[]; expected_revision: number }; writes.push(body)
        return writes.length === 1 ? response({ detail: 'Synthetic temporary refusal' }, 503) : response({ ...source, revision: 4, mapping: { sheets: body.sheets } })
      }
      if (url.pathname.endsWith('/sources/source-synthetic')) return response(source)
      return response({ detail: 'Unexpected fixture request' }, 500)
    })
    render(<SourceInspector packId={pack.id} sourceId={source.id} readOnly={false} onClose={vi.fn()} onChanged={changed} />)
    const group = await screen.findByRole('group', { name: 'Synthetic records' })
    const category = within(group).getByRole('combobox', { name: 'Recorded category' })
    expect(within(category).getByRole('option', { name: 'B · Work Group' })).toHaveValue('B')
    expect(within(category).getByRole('option', { name: 'C · Work Group · Hidden column' })).toHaveValue('C')
    await user.selectOptions(category, 'C')
    await user.selectOptions(within(group).getByRole('combobox', { name: 'Text date convention' }), 'DMY')
    await user.click(screen.getByRole('button', { name: 'Save mapping' }))
    expect(await screen.findByText('Synthetic temporary refusal')).toBeVisible()
    expect(category).toHaveValue('C')
    expect(changed).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Save mapping' }))
    await waitFor(() => expect(changed).toHaveBeenCalledOnce())
    expect(writes).toHaveLength(2)
    expect(writes[1]).toEqual(writes[0])
    expect(writes[1]).toMatchObject({ expected_revision: 3, sheets: [{ header_row: 2, date_format: 'DMY', columns: { sr_id: 'A', location: 'B', category: 'C' } }] })
  })

  it('preserves an unsaved mapping on Activity re-entry and refuses to silently adopt a changed revision', async () => {
    const user = userEvent.setup(), close = vi.fn(), changed = vi.fn()
    let revision = 3
    serve(() => response({ ...source, revision }))
    const panel = (mode: 'visible' | 'hidden') => <Activity mode={mode}><SourceInspector packId={pack.id} sourceId={source.id} readOnly={false} onClose={close} onChanged={changed} /></Activity>
    const view = render(panel('visible'))
    const group = await screen.findByRole('group', { name: 'Synthetic records' })
    await user.selectOptions(within(group).getByRole('combobox', { name: 'Recorded category' }), 'C')
    view.rerender(panel('hidden')); revision = 4; view.rerender(panel('visible'))
    expect(await screen.findByText(/saved source mapping changed while your draft was open/)).toBeVisible()
    expect(screen.getByRole('combobox', { name: 'Recorded category' })).toHaveValue('C')
    await user.click(screen.getByRole('button', { name: 'Reload saved mapping' }))
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Recorded category' })).toHaveValue(''))
  })
})

describe('protected evidence drill-down', () => {
  it('cancels an obsolete selection and displays a permission refusal without rendering its late records', async () => {
    const old = deferred<Response>(), requests: { body: { record_ids: string[] }; init: RequestInit }[] = []
    serve((_url, init) => {
      const body = JSON.parse(String(init.body)) as { record_ids: string[] }; requests.push({ body, init })
      return body.record_ids[0] === 'old-record' ? old.promise : response({ detail: 'Synthetic permission refusal' }, 403)
    })
    const close = vi.fn(), view = render(<RecordsDialog packId={pack.id} analysisId={analysis.id} selection={{ title: 'Synthetic first finding', query: { record_ids: ['old-record'] } }} onClose={close} />)
    await waitFor(() => expect(requests).toHaveLength(1))
    view.rerender(<RecordsDialog packId={pack.id} analysisId={analysis.id} selection={{ title: 'Synthetic second finding', query: { record_ids: ['restricted-record'] } }} onClose={close} />)
    expect(await screen.findByText('Synthetic permission refusal')).toBeVisible()
    expect(requests[0].init.signal?.aborted).toBe(true)
    await act(async () => { old.resolve(response({ records: [{ id: 'old-record', source_id: source.id, sheet: 'Synthetic records', source_row: 3, grain: 'mms_work_order', fields: { sr_id: 'OLD-PRIVATE-RESULT' } }], total: 1 })); await old.promise })
    expect(screen.queryByText('OLD-PRIVATE-RESULT')).not.toBeInTheDocument()
    expect(requests[1].body).toMatchObject({ record_ids: ['restricted-record'], offset: 0, limit: 25 })
    expect(requests[1].init.headers).toMatchObject({ Authorization: 'Bearer synthetic-test-token' })
    expect(screen.getByRole('button', { name: 'Retry read' })).toBeVisible()
  })
})

describe('scoped evidence assistant', () => {
  it('sends explicit pack/analysis/language context and preserves a failed question', async () => {
    const user = userEvent.setup(), questions: unknown[] = []
    serve((url, init) => {
      if (url.pathname.endsWith('/assistant')) { questions.push(JSON.parse(String(init.body))); return response({ detail: 'Synthetic answer unavailable' }, 503) }
      return response(pack)
    })
    render(<RmdAssistantPanel packId={pack.id} analysisId={analysis.id} />)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled())
    await user.type(screen.getByRole('textbox', { name: 'Evidence question' }), 'Explain the selected synthetic aggregate')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText('Synthetic answer unavailable')).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'Evidence question' })).toHaveValue('Explain the selected synthetic aggregate')
    expect(questions).toEqual([{ question: 'Explain the selected synthetic aggregate', analysis_id: analysis.id, language: 'en' }])
    expect(screen.getByText(/not stored in general chat history/)).toBeVisible()
  })

  it('keeps the same-context draft through Activity, aborts a pending answer and rechecks authorization', async () => {
    const user = userEvent.setup(), old = deferred<Response>(), signals: AbortSignal[] = []
    let reads = 0, denied = false
    serve((url, init) => {
      if (url.pathname.endsWith('/assistant')) { if (init.signal) signals.push(init.signal); return old.promise }
      reads += 1; return denied ? response({ detail: 'Synthetic access revoked' }, 404) : response(pack)
    })
    const panel = (mode: 'visible' | 'hidden') => <Activity mode={mode}><RmdAssistantPanel packId={pack.id} analysisId={analysis.id} /></Activity>
    const view = render(panel('visible'))
    await user.type(screen.getByRole('textbox', { name: 'Evidence question' }), 'Keep this synthetic draft')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    await waitFor(() => expect(signals).toHaveLength(1))
    view.rerender(panel('hidden')); denied = true; view.rerender(panel('visible'))
    expect(await screen.findByText('Synthetic access revoked')).toBeVisible()
    expect(reads).toBeGreaterThanOrEqual(2)
    expect(signals[0].aborted).toBe(true)
    expect(screen.getByRole('textbox', { name: 'Evidence question' })).toHaveValue('Keep this synthetic draft')
    await act(async () => { old.resolve(response({ text: 'LATE-PRIVATE-ANSWER', source: 'deterministic', citations: [] })); await old.promise })
    expect(screen.queryByText('LATE-PRIVATE-ANSWER')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()
  })

  it('clears evidence and draft when the principal changes', async () => {
    const user = userEvent.setup()
    serve((url) => url.pathname.endsWith('/assistant') ? response({ text: 'Synthetic scoped answer', source: 'deterministic', citations: [] }) : response(pack))
    const view = render(<RmdAssistantPanel packId={pack.id} analysisId={analysis.id} />)
    await user.type(screen.getByRole('textbox', { name: 'Evidence question' }), 'A private synthetic question')
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask' })).toBeEnabled())
    await user.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByText('Synthetic scoped answer')).toBeVisible()
    actor.subject = 'different-synthetic-owner'
    view.rerender(<RmdAssistantPanel packId={pack.id} analysisId={analysis.id} />)
    await waitFor(() => expect(screen.getByRole('textbox', { name: 'Evidence question' })).toHaveValue(''))
    expect(screen.queryByText('Synthetic scoped answer')).not.toBeInTheDocument()
  })
})

describe('governed report bridge', () => {
  it('waits for server confirmation and reuses its request key after an uncertain response', async () => {
    const user = userEvent.setup(), openRun = vi.fn(), first = deferred<Response>(), writes: unknown[] = []
    serve((url, init) => {
      if (url.pathname.endsWith('/review-run')) { writes.push(JSON.parse(String(init.body))); return writes.length === 1 ? first.promise : response({ run_id: 'run-synthetic' }) }
      if (url.pathname.endsWith('/actions')) return response({ actions: [] })
      if (url.pathname.endsWith(`/analyses/${analysis.id}`)) return response(analysis)
      if (url.pathname === '/api/rmd/packs') return response({ packs: [pack] })
      if (url.pathname.endsWith(`/packs/${pack.id}`)) return response(pack)
      return response({ detail: 'Unexpected fixture request' }, 500)
    })
    render(<RmdView onOpenRun={openRun} />)
    await user.click(await screen.findByRole('button', { name: 'Review report' }))
    expect(openRun).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Review report' })).toBeDisabled()
    await act(async () => { first.resolve(response({ detail: 'Synthetic uncertain response' }, 503)); await first.promise })
    expect(await screen.findByText('Synthetic uncertain response')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Review report' }))
    await waitFor(() => expect(openRun).toHaveBeenCalledWith('run-synthetic'))
    expect(writes).toHaveLength(2)
    expect(writes[1]).toEqual(writes[0])
    expect(writes[0]).toMatchObject({ idempotency_key: expect.any(String) })
  })
})
