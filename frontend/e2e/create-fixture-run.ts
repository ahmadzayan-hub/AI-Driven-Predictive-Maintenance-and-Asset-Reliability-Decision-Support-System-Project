import { randomUUID } from 'node:crypto'
import type { APIRequestContext } from '@playwright/test'

/** Retry only a reset during creation, using the API's existing replay contract.
 * The key is allocated once, so a lost response cannot create a second run.
 * Advancing, approving and UI assertions deliberately have no retry here.
 */
export async function createFixtureRun(request: APIRequestContext, goal: string) {
  const response = await request.post('/api/runs', {
    data: { goal },
    headers: { 'Idempotency-Key': `e2e-${randomUUID()}` },
    maxRetries: 1,
  })
  if (![200, 201].includes(response.status())) {
    throw new Error(`Fixture run creation returned HTTP ${response.status()}`)
  }
  const run = await response.json()
  if (run === null || typeof run !== 'object' ||
      typeof run.id !== 'string' || typeof run.state !== 'string') {
    throw new Error('Fixture run creation returned an invalid run')
  }
  return run as { id: string; state: string }
}
