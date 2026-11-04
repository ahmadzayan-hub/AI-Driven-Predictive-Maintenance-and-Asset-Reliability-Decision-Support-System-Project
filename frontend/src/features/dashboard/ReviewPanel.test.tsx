import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { applyLocale } from '../../i18n'
import type { RunExecutive } from '../../shared/types'
import ReviewPanel from './ReviewPanel'

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const sha = (c: string) => c.repeat(64)
const entry = (state: string, artifact: string | null, review: object | null = null) => ({ state, artifact_sha256: artifact, review })
const state = (slides = entry('draft', sha('c'))) => ({ snapshot_id: sha('s'), language: 'en', history: [], video: null,
  video_renderer: { available: false, missing: ['espeak-ng'] },
  formats: { dashboard: entry('draft', sha('s')), html: entry('changed_since_review', sha('a'), { id: '1', format: 'html', decision: 'approved', comment: '', reviewer: 'alice', created_at: '2026-11-04T08:00:00Z', language: 'en' }),
    docx: entry('draft', sha('d')), slides, video: entry('not_rendered', null) } })
const brief = { snapshot_id: sha('s') } as RunExecutive
afterEach(() => { vi.restoreAllMocks(); act(() => applyLocale('en')) })

it('shows each output’s state, records a decision on the exact file and says when a host cannot render video', async () => {
  let current = state()
  const approved = state(entry('approved', sha('c'), { id: '2', format: 'slides', decision: 'approved', comment: 'ok', reviewer: 'alice', created_at: '2026-11-04T09:00:00Z', language: 'en' }))
  const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (_url, init) => {
    if (init?.method === 'POST') { current = approved; return json({ formats: approved.formats }) }
    return json(current)
  })
  render(<ReviewPanel runId="r1" brief={brief} filters={[]} language="en" canReview />)
  const slides = (await screen.findByText('Slides')).closest('li')!
  expect(within(slides).getByText('Draft · not reviewed')).toBeInTheDocument()
  expect(screen.getByText('Changed since review · needs a new review')).toBeInTheDocument()
  expect(screen.getByText('Video cannot be rendered on this host: espeak-ng.')).toBeInTheDocument()
  // Asking for changes needs a comment first.
  expect(within(slides).getByRole('button', { name: 'Request changes' })).toBeDisabled()
  fireEvent.click(within(slides).getByRole('button', { name: 'Approve' }))
  await waitFor(() => expect(within(slides).getByText('Approved')).toBeInTheDocument())
  const sent = JSON.parse(String(fetch.mock.calls.find(([, init]) => init?.method === 'POST')![1]!.body))
  expect(sent).toMatchObject({ format: 'slides', expected_snapshot_id: sha('s'), artifact_sha256: sha('c'), decision: 'approved' })
})

it('reads in Arabic and offers no decision to a reader who cannot review', async () => {
  applyLocale('ar')
  vi.spyOn(globalThis, 'fetch').mockImplementation(async () => json(state()))
  render(<ReviewPanel runId="r1" brief={brief} filters={[]} language="ar" canReview={false} />)
  expect(await screen.findByText('المراجعة قبل النشر')).toBeInTheDocument()
  expect(screen.getAllByText('مسودة · لم تُراجع').length).toBeGreaterThan(0)
  expect(screen.queryByRole('button', { name: 'اعتماد' })).toBeNull()
})
