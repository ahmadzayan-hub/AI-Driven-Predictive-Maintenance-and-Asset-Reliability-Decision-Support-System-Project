import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../shared/api'
import { createRunStore } from '../features/runs/runStore'
import { runFixture } from './run-fixture'

afterEach(() => vi.useRealTimers())

describe('shared run scheduler', () => {
  it('uses one advancing request for multiple observers', async () => {
    vi.useFakeTimers()
    const gateway = { getRun: vi.fn().mockResolvedValue(runFixture()), advanceRun: vi.fn().mockResolvedValue(runFixture({ paused: true })) }
    const store = createRunStore(gateway)
    const first = store.watch('run-test', true)
    const second = store.watch('run-test', true)
    await vi.advanceTimersByTimeAsync(350)
    expect(gateway.getRun).toHaveBeenCalledTimes(1)
    expect(gateway.advanceRun).toHaveBeenCalledTimes(1)
    first(); second(); store.reset()
  })
  it('never advances a read-only assistant card', async () => {
    vi.useFakeTimers()
    const gateway = { getRun: vi.fn().mockResolvedValue(runFixture()), advanceRun: vi.fn() }
    const store = createRunStore(gateway)
    const stop = store.watch('run-test')
    await vi.advanceTimersByTimeAsync(2800)
    expect(gateway.getRun).toHaveBeenCalledTimes(2)
    expect(gateway.advanceRun).not.toHaveBeenCalled()
    stop(); store.reset()
  })
  it('polls server-driven runs without sending advance requests', async () => {
    vi.useFakeTimers()
    const detail = runFixture({ execution: { mode: 'worker', poll_after_ms: 2500 } })
    const gateway = { getRun: vi.fn().mockResolvedValue(detail), advanceRun: vi.fn() }
    const store = createRunStore(gateway)
    const first = store.watch('run-test', true)
    const second = store.watch('run-test', true)
    await vi.advanceTimersByTimeAsync(5100)
    expect(gateway.getRun).toHaveBeenCalledTimes(3)
    expect(gateway.advanceRun).not.toHaveBeenCalled()
    first(); second()
    await vi.advanceTimersByTimeAsync(10000)
    expect(gateway.getRun).toHaveBeenCalledTimes(3)
    store.reset()
  })
  it('switches to reads when a response advertises worker execution', async () => {
    vi.useFakeTimers()
    const workerRun = runFixture({ execution: { mode: 'worker', poll_after_ms: 2500 } })
    const gateway = { getRun: vi.fn().mockResolvedValue(workerRun), advanceRun: vi.fn().mockResolvedValue(workerRun) }
    const store = createRunStore(gateway)
    store.receive(runFixture())
    const stop = store.watch('run-test', true)
    await vi.advanceTimersByTimeAsync(5100)
    expect(gateway.advanceRun).not.toHaveBeenCalled()
    expect(gateway.getRun).toHaveBeenCalledTimes(3)
    stop(); store.reset()
  })
  it('keeps a decision pending until its server response and blocks a second submission', async () => {
    let resolve!: (value: ReturnType<typeof runFixture>) => void
    const pending = new Promise<ReturnType<typeof runFixture>>((done) => { resolve = done })
    const store = createRunStore({ getRun: vi.fn(), advanceRun: vi.fn() })
    store.receive(runFixture())
    const post = vi.fn(() => pending)
    const first = store.mutate('run-test', post)
    await Promise.resolve()
    expect(store.get('run-test').pending).toBe(true)
    expect(store.get('run-test').detail?.report?.published_path).toBeUndefined()
    expect(await store.mutate('run-test', post)).toBeNull()
    resolve(runFixture({ state: 'completed' }))
    await first
    expect(post).toHaveBeenCalledTimes(1)
    expect(store.get('run-test').pending).toBe(false)
    store.reset()
  })
  it('reconciles a refused decision by reading and never replays the POST', async () => {
    const gateway = { getRun: vi.fn().mockResolvedValue(runFixture({ state: 'awaiting_approval' })), advanceRun: vi.fn() }
    const store = createRunStore(gateway)
    store.receive(runFixture())
    const post = vi.fn().mockRejectedValue(new ApiError('Artifact changed', 409))
    await expect(store.mutate('run-test', post)).rejects.toThrow('Artifact changed')
    expect(post).toHaveBeenCalledTimes(1)
    expect(gateway.getRun).toHaveBeenCalledTimes(1)
    expect(store.get('run-test').detail?.state).toBe('awaiting_approval')
    expect(store.get('run-test').interrupted).toBe(true)
    expect(store.get('run-test').error?.message).toBe('Artifact changed')
    store.reset()
  })
})
