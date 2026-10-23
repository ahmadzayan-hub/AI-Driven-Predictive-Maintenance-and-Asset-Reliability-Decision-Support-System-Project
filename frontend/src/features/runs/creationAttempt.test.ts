import { webcrypto } from 'node:crypto'
import { afterEach, expect, it, vi } from 'vitest'
import { CreationAttempt } from './creationAttempt'

afterEach(() => { sessionStorage.clear(); vi.unstubAllGlobals(); vi.restoreAllMocks() })

it('recovers an uncertain request after remount without storing its private payload', async () => {
  vi.stubGlobal('crypto', webcrypto)
  const payload = JSON.stringify({ goal: 'PRIVATE_QUESTION', csv: 'PRIVATE_DATASET_ROWS', assumptions: { cost: 12 } })
  const first = await new CreationAttempt().forRequest('alice-session', payload)
  const recovered = await new CreationAttempt().forRequest('alice-session', payload)
  expect(recovered).toBe(first)
  const saved = sessionStorage.getItem('aos-draft:alice-session:analysis-attempt')!
  expect(saved).not.toContain('PRIVATE_')
  expect(JSON.parse(saved)).toEqual({ key: first, fingerprint: expect.stringMatching(/^[a-f0-9]{64}$/) })
  expect(await new CreationAttempt().forRequest('bob-session', payload)).not.toBe(first)
  expect(await new CreationAttempt().forRequest('alice-session', payload + ' changed')).not.toBe(first)
})

it('starts a fresh attempt only after confirmation and retains a live retry if storage is blocked', async () => {
  vi.stubGlobal('crypto', webcrypto)
  const attempt = new CreationAttempt()
  const first = await attempt.forRequest('s', 'same request')
  attempt.complete('s')
  expect(sessionStorage.length).toBe(0)
  expect(await attempt.forRequest('s', 'same request')).not.toBe(first)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('blocked') })
  const live = new CreationAttempt()
  const key = await live.forRequest('new', 'private rows remain in memory')
  expect(await live.forRequest('new', 'private rows remain in memory')).toBe(key)
})
