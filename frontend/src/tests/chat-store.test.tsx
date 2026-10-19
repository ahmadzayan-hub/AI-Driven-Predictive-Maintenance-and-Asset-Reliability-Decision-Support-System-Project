import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { StoreProvider, useStore } from '../app/store'
import { api, ApiError, type MessageResult } from '../shared/api'
import type { SessionState } from '../shared/types'

function session(id = 'test-session'): SessionState {
  return { session_id: id, agent_name: 'Agentic OS', version: 'test', welcome: '',
    ended: false, created_at: '2026-10-19T00:00:00Z', transcript: [],
    preferences: { language: 'English' }, memory: {}, memory_entries: [], history: [],
    memory_persisted: false, commands: [] }
}
function response(id = 'test-session', question = 'First', answer = 'Reply'): MessageResult {
  const state = session(id)
  state.transcript = [
    { id: 1, role: 'user', text: question, time: state.created_at },
    { id: 2, role: 'agent', text: answer, time: state.created_at, source: 'model', action: 'chat' },
  ]
  return { reply: state.transcript[1], state }
}
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (reason: unknown) => void
  const promise = new Promise<T>((a, b) => { resolve = a; reject = b })
  return { promise, resolve, reject }
}
beforeEach(() => {
  vi.restoreAllMocks()
  localStorage.clear()
  vi.spyOn(api, 'authConfig').mockResolvedValue({ mode: 'local', provider_url: '', publishable_key: '', flows: [] })
  vi.spyOn(api, 'createSession').mockImplementation(async () => session())
})
async function setup() {
  const hook = renderHook(() => useStore(), { wrapper: StoreProvider })
  await waitFor(() => expect(hook.result.current.session?.session_id).toBe('test-session'))
  return hook
}
describe('Miyaar chat request continuity', () => {
  it('shows the pending question, blocks same-tick duplicates and accepts the next turn', async () => {
    const first = deferred<MessageResult>()
    const send = vi.spyOn(api, 'sendMessage').mockReturnValueOnce(first.promise).mockResolvedValueOnce(response('test-session','Follow-up','Second reply'))
    const { result } = await setup()
    let promise!: Promise<boolean>
    act(() => { promise = result.current.send('First'); void result.current.send('duplicate') })
    expect(result.current.pendingText).toBe('First')
    expect(send).toHaveBeenCalledTimes(1)
    await act(async () => { first.resolve(response()); await promise })
    expect(result.current.pendingText).toBeNull()
    expect(result.current.session?.transcript[1].text).toBe('Reply')
    await act(async () => { await result.current.send('Follow-up') })
    expect(send).toHaveBeenLastCalledWith('test-session','Follow-up')
    expect(result.current.session?.transcript[1].text).toBe('Second reply')
  })
  it('retains the failed question and exposes the actual error before manual retry', async () => {
    vi.spyOn(api, 'sendMessage').mockRejectedValueOnce(new ApiError('Rate limited',429)).mockResolvedValueOnce(response())
    const { result } = await setup()
    await act(async () => { expect(await result.current.send('First')).toBe(false) })
    expect(result.current.failedText).toBe('First')
    expect(result.current.requestError).toBe('Rate limited')
    expect(result.current.sending).toBe(false)
    await act(async () => { await result.current.retryFailed() })
    expect(result.current.failedText).toBeNull()
    expect(result.current.requestError).toBeNull()
  })
  it('does not replace a new session with a reply from the previous session', async () => {
    const request = deferred<MessageResult>()
    vi.spyOn(api, 'sendMessage').mockReturnValue(request.promise)
    const { result } = await setup()
    let send!: Promise<boolean>
    act(() => { send = result.current.send('Old session') })
    vi.mocked(api.createSession).mockResolvedValueOnce(session('new-session'))
    await act(async () => { await result.current.start() })
    await act(async () => { request.resolve(response()); await send })
    expect(result.current.session?.session_id).toBe('new-session')
    expect(result.current.session?.transcript).toHaveLength(0)
    expect(result.current.sending).toBe(false)
  })
  it('keeps an ended session closed when an earlier message finishes later', async () => {
    const request = deferred<MessageResult>()
    vi.spyOn(api, 'sendMessage').mockReturnValue(request.promise)
    vi.spyOn(api, 'endSession').mockResolvedValue({ ...session(), ended: true })
    const { result } = await setup()
    let send!: Promise<boolean>
    act(() => { send = result.current.send('Still waiting') })
    await act(async () => { await result.current.endSession() })
    await act(async () => { request.resolve(response()); await send })
    expect(result.current.session?.ended).toBe(true)
    expect(result.current.sending).toBe(false)
    expect(result.current.pendingText).toBeNull()
  })
  it('ignores an old response after sign-out', async () => {
    const request = deferred<MessageResult>()
    vi.spyOn(api, 'sendMessage').mockReturnValue(request.promise)
    const { result } = await setup()
    let send!: Promise<boolean>
    act(() => { send = result.current.send('Private question') })
    act(() => result.current.signOut())
    await act(async () => { request.resolve(response()); await send })
    expect(result.current.session).toBeNull()
    expect(result.current.pendingText).toBeNull()
    expect(result.current.needsSignIn).toBe(true)
  })
  it('returns to sign-in when a message receives an unauthorized response', async () => {
    vi.spyOn(api, 'sendMessage').mockRejectedValue(new ApiError('Expired',401))
    const { result } = await setup()
    await act(async () => { await result.current.send('First') })
    expect(result.current.session).toBeNull()
    expect(result.current.failedText).toBeNull()
    expect(result.current.needsSignIn).toBe(true)
  })
  it('treats an empty backend reply as a failure instead of fabricating an answer', async () => {
    vi.spyOn(api, 'sendMessage').mockResolvedValue(response('test-session','First',' '))
    const { result } = await setup()
    await act(async () => { expect(await result.current.send('First')).toBe(false) })
    expect(result.current.failedText).toBe('First')
    expect(result.current.session?.transcript).toHaveLength(0)
  })
})
