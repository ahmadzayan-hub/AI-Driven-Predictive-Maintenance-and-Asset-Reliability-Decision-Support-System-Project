// Real loopback HTTP faults exercise Playwright's request-level retry behavior.
// The production replay contract is also covered in tests/test_runs.py.
import test from 'node:test'
import assert from 'node:assert/strict'
import { createServer } from 'node:http'
import { request } from '@playwright/test'
import { createFixtureRun } from '../../e2e/create-fixture-run.ts'

async function endpoint(t, handler) {
  const server = createServer(handler)
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
  const client = await request.newContext({
    baseURL: `http://127.0.0.1:${server.address().port}`,
    timeout: 5_000,
  })
  t.after(async () => {
    await client.dispose()
    server.closeAllConnections()
    await new Promise(resolve => server.close(resolve))
  })
  return client
}

test('fixture creation uses a fresh key for each separate run', async t => {
  const keys = []
  const client = await endpoint(t, (req, res) => {
    assert.equal(req.url, '/api/runs')
    keys.push(req.headers['idempotency-key'])
    res.writeHead(201, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({ id: `run-${keys.length}`, state: 'queued' }))
  })
  assert.equal((await createFixtureRun(client, 'synthetic')).id, 'run-1')
  assert.equal((await createFixtureRun(client, 'synthetic')).id, 'run-2')
  assert.match(keys[0], /^e2e-/)
  assert.notEqual(keys[0], keys[1])
})

test('a response lost after creation replays the same key without a second run', async t => {
  const runs = new Map()
  const keys = []
  const client = await endpoint(t, (req, res) => {
    const key = req.headers['idempotency-key']
    keys.push(key)
    if (!runs.has(key)) {
      runs.set(key, { id: 'created-before-reset', state: 'queued' })
      req.socket.resetAndDestroy()
      return
    }
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(runs.get(key)))
  })
  assert.equal((await createFixtureRun(client, 'synthetic')).id, 'created-before-reset')
  assert.equal(keys.length, 2)
  assert.equal(keys[0], keys[1])
  assert.equal(runs.size, 1)
})

test('a second connection reset still fails after one retry', async t => {
  let calls = 0
  const client = await endpoint(t, req => {
    calls += 1
    req.socket.resetAndDestroy()
  })
  await assert.rejects(createFixtureRun(client, 'synthetic'), /ECONNRESET/)
  assert.equal(calls, 2)
})

for (const status of [409, 503]) {
  test(`HTTP ${status} is not retried or accepted as success`, async t => {
    let calls = 0
    const client = await endpoint(t, (_req, res) => {
      calls += 1
      res.writeHead(status, { 'Content-Type': 'application/json' })
      res.end('{}')
    })
    await assert.rejects(createFixtureRun(client, 'synthetic'), new RegExp(`HTTP ${status}`))
    assert.equal(calls, 1)
  })
}

for (const payload of [{}, null]) {
  test(`malformed success ${JSON.stringify(payload)} is still a failure`, async t => {
    const client = await endpoint(t, (_req, res) => {
      res.writeHead(201, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify(payload))
    })
    await assert.rejects(createFixtureRun(client, 'synthetic'), /invalid run/)
  })
}
