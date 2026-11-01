import { createRef, useRef } from 'react'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { StoreProvider, useStore } from '../app/store'
import { parseRoute } from '../app/routing'
import { ChatView } from '../features/chat/ChatView'
import { DataChatContext } from '../features/chat/DataChatContext'
import { dataChatMessages } from '../features/chat/dataChatMessages'
import type { ComposerHandle } from '../features/chat/Composer'
import { api, ApiError } from '../shared/api'
import type { SessionState } from '../shared/types'
import { applyLocale } from '../i18n'

const initial = (): SessionState => ({ session_id: 'chat-synthetic', agent_name: 'Miyaar',
  data_chat_labels: Object.fromEntries(Object.entries(dataChatMessages.en).map(([key, value]) => [key.replace('dataChat.', ''), value])) as SessionState['data_chat_labels'],
  version: 'test', welcome: '', ended: false, created_at: '', transcript: [],
  preferences: { language: 'English' }, memory: {}, memory_entries: [], history: [],
  memory_persisted: true, commands: [], assistant_status: { code: 'not_configured',
    message: 'Synthetic model is not enabled; workspace commands remain available.', inference_verified: false } })

function Workspace() {
  const store = useStore()
  const composer = useRef<ComposerHandle>(null)
  if (!store.session) return <p>{store.bootError || 'Waiting for session'}</p>
  return <ChatView session={store.session} sending={store.sending} failedText={store.failedText}
    pendingText={store.pendingText} requestError={store.requestError} connectionStatus={store.status}
    offline={store.status === 'offline'} userName={null} onSend={store.send} onRetry={store.retryFailed}
    onDismissFailed={store.dismissFailed} composerRef={composer} />
}
beforeEach(() => {
  vi.restoreAllMocks(); localStorage.clear(); applyLocale('en')
  vi.spyOn(api, 'authConfig').mockResolvedValue({ mode: 'local', provider_url: '', publishable_key: '', flows: [] })
  vi.spyOn(api, 'createSession').mockResolvedValue(initial())
})
afterEach(() => { act(() => applyLocale('en')); vi.restoreAllMocks() })

it('keeps a collapsed report disclosure and actual model notice beside the composer', async () => {
  const view = render(<StoreProvider><Workspace /></StoreProvider>)
  const context = await screen.findByRole('region', { name: 'Workspace context' })
  expect(within(context).getByText(initial().assistant_status!.message)).toBeVisible()
  const details = context.querySelector('details')!
  expect(details).not.toHaveAttribute('open')
  expect(view.container.querySelector('.assistant-workspace > aside')).toBeNull()
  expect(context.nextElementSibling).toHaveClass('composer')
  await userEvent.setup().click(within(context).getByText(/Data for this chat:/))
  expect(within(context).getByRole('button', { name: 'Show my reports' })).toBeEnabled()
  expect(view.container.querySelectorAll('.tool-cards')).toHaveLength(1)
  expect(view.container.querySelector('.miyaar-status')).toBeNull()
  expect(view.container.querySelector('.chat textarea')).toBeInTheDocument()
})

it.each(['en', 'ar'] as const)('requires explicit report selection and retains the returned context in %s', async language => {
  applyLocale(language)
  const localized = { ...initial(), data_chat_labels: Object.fromEntries(Object.entries(dataChatMessages[language]).map(([key, value]) => [key.replace('dataChat.', ''), value])) as SessionState['data_chat_labels'] }
  const selected = { run_id: 'owned-report', dataset_id: 'd1', dataset_name: 'synthetic.csv',
    source_sha256: 'a'.repeat(64), analysis_revision: 'b'.repeat(64), filters: [], records: 3, total_records: 3 }
  const load = vi.spyOn(api, 'dataContext').mockResolvedValue({ selected: null,
    choices: [{ run_id: selected.run_id, dataset_name: selected.dataset_name, state: 'completed' }] })
  const save = vi.spyOn(api, 'selectDataContext').mockResolvedValue({ ...initial(), data_context: selected })
  const view = render(<DataChatContext session={localized} disabled={false} />)
  const user = userEvent.setup()
  expect(view.container.querySelector('details')).not.toHaveAttribute('open')
  await user.click(view.container.querySelector('summary')!)
  await user.click(screen.getByRole('button', { name: language === 'ar' ? 'عرض تقاريري' : 'Show my reports' }))
  const select = await screen.findByRole('combobox')
  expect(select).toHaveValue('')
  expect(save).not.toHaveBeenCalled()
  await user.selectOptions(select, selected.run_id)
  await user.click(screen.getByRole('button', { name: language === 'ar' ? 'استخدام هذا التقرير' : 'Use this report' }))
  await waitFor(() => expect(save).toHaveBeenCalledWith(initial().session_id, selected.run_id))
  expect(load).toHaveBeenCalledWith(initial().session_id)
  expect(await screen.findByText(selected.run_id, { selector: 'bdi' })).toBeVisible()
  await user.click(view.container.querySelector('summary')!)
  expect(view.container.querySelector('details')).not.toHaveAttribute('open')
  expect(view.container.querySelector('summary')).toHaveTextContent(selected.dataset_name)
  await user.click(view.container.querySelector('summary')!)
  expect(screen.getByRole('combobox')).toHaveValue(selected.run_id)
  expect(save).toHaveBeenCalledTimes(1)
  view.unmount()
  const restored = render(<DataChatContext session={{ ...initial(), data_context: selected }} disabled={false} />)
  expect(restored.container.querySelector('summary')).toHaveTextContent(selected.dataset_name)
})

it('does not show a confirmed selection when saving fails', async () => {
  vi.spyOn(api, 'dataContext').mockResolvedValue({ selected: null,
    choices: [{ run_id: 'stale', dataset_name: 'synthetic.csv', state: 'completed' }] })
  vi.spyOn(api, 'selectDataContext').mockRejectedValue(new ApiError('Stale report', 409))
  const view = render(<DataChatContext session={initial()} disabled={false} />)
  const user = userEvent.setup()
  expect(view.container.querySelector('details')).not.toHaveAttribute('open')
  await user.click(view.container.querySelector('summary')!)
  await user.click(screen.getByRole('button', { name: 'Show my reports' }))
  await user.selectOptions(await screen.findByRole('combobox'), 'stale')
  await user.click(screen.getByRole('button', { name: 'Use this report' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not confirm')
  expect(view.container.querySelector('summary')).toHaveTextContent('No report selected')
})

it('routes both user-facing addresses to the same workspace', () => {
  expect(parseRoute('#/workspace')).toEqual({ tab: 'chat' })
  expect(parseRoute('#/assistant')).toEqual({ tab: 'chat' })
})

it('shows model availability while connected and submits a question through the store and API', async () => {
  const state = initial()
  state.transcript = [{ id: 1, role: 'user', text: 'Synthetic question', time: '' },
    { id: 2, role: 'agent', text: 'Synthetic model answer', source: 'model', provider: 'ollama', action: 'chat', time: '' }]
  const send = vi.spyOn(api, 'sendMessage').mockResolvedValue({ reply: state.transcript[1], state })
  render(<StoreProvider><Workspace /></StoreProvider>)
  expect(await screen.findByText(initial().assistant_status!.message)).toBeVisible()
  const user = userEvent.setup()
  await user.type(screen.getByRole('textbox'), 'Synthetic question{Enter}')
  expect(await screen.findByText('Synthetic model answer')).toBeVisible()
  expect(send).toHaveBeenCalledExactlyOnceWith('chat-synthetic', 'Synthetic question')
  expect(screen.getByText(initial().assistant_status!.message)).toBeVisible()
})

it('keeps a stored session on server failure instead of losing workspace state', async () => {
  localStorage.setItem('aos-session', 'saved-session')
  vi.spyOn(api, 'getSession').mockRejectedValue(new ApiError('Synthetic server unavailable', 503))
  render(<StoreProvider><Workspace /></StoreProvider>)
  expect(await screen.findByText('Synthetic server unavailable')).toBeVisible()
  expect(api.createSession).not.toHaveBeenCalled()
  expect(localStorage.getItem('aos-session')).toBe('saved-session')
})

it('restores a saved transcript and uses a new session only after an explicit 404', async () => {
  localStorage.setItem('aos-session', 'saved-session')
  const state = initial()
  state.transcript = [{ id: 1, role: 'agent', text: 'Saved workspace reply', time: '', source: 'rules' }]
  vi.spyOn(api, 'getSession').mockResolvedValue(state)
  const view = render(<StoreProvider><Workspace /></StoreProvider>)
  expect(await screen.findByText('Saved workspace reply')).toBeVisible()
  expect(api.createSession).not.toHaveBeenCalled()
  view.unmount()
  vi.mocked(api.getSession).mockRejectedValue(new ApiError('Expired session', 404))
  render(<StoreProvider><Workspace /></StoreProvider>)
  await waitFor(() => expect(api.createSession).toHaveBeenCalledOnce())
})

it('clears context only after the server confirms and preserves it across disclosure toggles', async () => {
  const selected = { run_id: 'owned-report', dataset_id: 'd1', dataset_name: 'synthetic.csv',
    source_sha256: 'a'.repeat(64), analysis_revision: 'b'.repeat(64), filters: [], records: 3, total_records: 3 }
  const save = vi.spyOn(api, 'selectDataContext').mockResolvedValue({ ...initial(), data_context: null })
  const view = render(<DataChatContext session={{ ...initial(), data_context: selected }} disabled={false} />)
  const user = userEvent.setup()
  expect(view.container.querySelector('summary')).toHaveTextContent('synthetic.csv')
  await user.click(view.container.querySelector('summary')!)
  await user.click(screen.getByRole('button', { name: 'Clear selection' }))
  await waitFor(() => expect(view.container.querySelector('summary')).toHaveTextContent('No report selected'))
  expect(save).toHaveBeenCalledExactlyOnceWith('chat-synthetic', null)
})

it.each([true, false])('keeps context actions disabled when unavailable: %s', async ended => {
  const view = render(<DataChatContext session={{ ...initial(), ended }} disabled />)
  await userEvent.setup().click(view.container.querySelector('summary')!)
  expect(screen.getByRole('button', { name: 'Show my reports' })).toBeDisabled()
})

it('emphasizes analysis without changing any workspace action or inventing model readiness', async () => {
  const onAction = vi.fn()
  const view = render(<ChatView session={initial()} sending={false} failedText={null}
    offline={false} userName={null} onSend={vi.fn()} onRetry={vi.fn()} onDismissFailed={vi.fn()}
    composerRef={createRef<ComposerHandle>()} onAction={onAction} />)
  const primary = screen.getByRole('button', { name: /Analyze data/ })
  expect(primary).toHaveClass('miyaar-action--primary')
  expect(view.container.querySelectorAll('.miyaar-action--primary')).toHaveLength(1)
  const actions = view.container.querySelectorAll('.miyaar-actions button')
  const user = userEvent.setup()
  for (const action of actions) await user.click(action)
  expect(onAction.mock.calls.map(call => call[0])).toEqual(['analyse', 'assets', 'report', 'compare', 'approvals'])
  expect(view.container.querySelector('.miyaar-toolbar')).toHaveTextContent('Ask Miyaar')
  expect(view.container.querySelector('.miyaar-toolbar')).not.toHaveTextContent('AI-Powered')
  expect(screen.queryByText('Ready')).not.toBeInTheDocument()
})
