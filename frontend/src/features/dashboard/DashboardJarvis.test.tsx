import { act, fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { DashboardJarvis } from './DashboardJarvis'
import * as transport from '../../shared/api'
import { applyLocale } from '../../i18n'
import { ReadOnlyContext } from '../../shared/readOnly'
import type { SessionState, TableFilter } from '../../shared/types'

vi.mock('../chat/JarvisWorkspace', () => ({ JarvisWorkspace: ({ session, embedded }: { session: SessionState; embedded: boolean }) =>
  <div>Bound {session.session_id} {embedded ? 'embedded' : 'standalone'}</div> }))
const session = { session_id: 'js1' } as SessionState
const props = { runId: 'run1', datasetName: 'SYNTHETIC.csv', filters: [] as TableFilter[], children: <p>Chart evidence</p> }
beforeEach(() => {
  vi.restoreAllMocks(); applyLocale('en')
  vi.spyOn(transport.api, 'createSession').mockResolvedValue(session)
  vi.spyOn(transport, 'request').mockResolvedValue(session)
})
it('binds only on explicit action, deduplicates requests and retains the charts', async () => {
  render(<DashboardJarvis {...props} />)
  expect(transport.api.createSession).not.toHaveBeenCalled()
  const connect = screen.getByRole('button', { name: 'Connect this view to Jarvis' })
  fireEvent.click(connect); fireEvent.click(connect)
  expect(await screen.findByText('Bound js1 embedded')).toBeVisible()
  expect(transport.api.createSession).toHaveBeenCalledTimes(1)
  expect(transport.request).toHaveBeenCalledWith('/api/sessions/js1/data-context', expect.objectContaining({ body: JSON.stringify({ run_id: 'run1', filters: [] }) }))
  expect(screen.getByText('Chart evidence')).toBeVisible()
})
it('clears previous scope, requires reconnect and ignores late binding responses', async () => {
  let resolve!: (value: SessionState) => void
  vi.mocked(transport.request).mockReturnValueOnce(new Promise(r => { resolve = r }))
  const view = render(<DashboardJarvis {...props} />)
  fireEvent.click(screen.getByRole('button', { name: 'Connect this view to Jarvis' }))
  await act(async () => {})
  const filters: TableFilter[] = [{ column: 'Asset_ID', op: 'in', values: ['SYN-C'] }]
  view.rerender(<DashboardJarvis {...props} filters={filters} />)
  await act(async () => resolve(session))
  expect(screen.queryByText('Bound js1 embedded')).not.toBeInTheDocument()
  expect(screen.getByRole('status')).toHaveTextContent('The view changed')
  fireEvent.click(screen.getByRole('button', { name: 'Connect this view to Jarvis' }))
  expect(await screen.findByText('Bound js1 embedded')).toBeVisible()
  expect(transport.request).toHaveBeenLastCalledWith('/api/sessions/js1/data-context', expect.objectContaining({ body: JSON.stringify({ run_id: 'run1', filters }) }))
})
it('keeps permission denial and read-only state explicit without losing analytics', async () => {
  vi.mocked(transport.request).mockRejectedValue(new Error('403'))
  const view = render(<DashboardJarvis {...props} />)
  fireEvent.click(screen.getByRole('button', { name: 'Connect this view to Jarvis' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('outside your permissions')
  expect(screen.getByText('Chart evidence')).toBeVisible()
  view.unmount(); applyLocale('ar')
  render(<ReadOnlyContext value><DashboardJarvis {...props} /></ReadOnlyContext>)
  expect(screen.getByRole('button', { name: 'ربط هذا العرض بـ Jarvis' })).toBeDisabled()
  expect(document.documentElement.dir).toBe('rtl')
})
