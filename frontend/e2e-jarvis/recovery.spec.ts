import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('aos-onboarded', '1'); localStorage.setItem('aos-locale', 'en')
  })
})

test('missing session on reload preserves the draft and requires explicit replacement before one send', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('aos-session', 'expired-synthetic-session')
    sessionStorage.setItem('aos-draft:expired-synthetic-session:composer', '/help')
  })
  const writes: string[] = []
  page.on('request', r => { if (r.method() === 'POST') writes.push(new URL(r.url()).pathname) })
  await page.goto('/#/assistant')
  await expect(page.getByText('This session is no longer on this server.', { exact: false })).toBeVisible()
  expect(writes.filter(p => p === '/api/sessions')).toHaveLength(0)
  await page.getByRole('button', { name: 'New session · keep draft' }).click()
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toHaveValue('/help')
  expect(writes.filter(p => p.endsWith('/messages'))).toHaveLength(0)
  const reply = page.waitForResponse(r => r.url().endsWith('/messages') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Send message', exact: true }).click()
  expect((await reply).status()).toBe(200)
  await expect(page.getByRole('textbox', { name: 'Message', exact: true })).toHaveValue('')
  expect(writes.filter(p => p.endsWith('/messages'))).toHaveLength(1)
  expect(await page.evaluate(() => sessionStorage.getItem('aos-draft:expired-synthetic-session:composer'))).toBe('/help')
})

test('lost reply is checked against the accepted conversation without a second send', async ({ page }) => {
  let posts = 0
  await page.route('**/messages', async route => {
    posts++; await route.fetch(); await route.abort('failed')
  })
  await page.goto('/#/assistant')
  const input = page.getByRole('textbox', { name: 'Message', exact: true })
  await input.fill('/help')
  await page.getByRole('button', { name: 'Send message', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('could not be confirmed')
  await expect(input).toHaveValue('/help')
  await expect(page.getByRole('button', { name: 'Send message', exact: true })).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Keep draft for manual send' })).toBeDisabled()
  await page.getByRole('button', { name: 'Check conversation', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('No message was resent')
  await expect(page.getByRole('log')).toContainText('/help')
  await expect(input).toHaveValue('/help')
  expect(posts).toBe(1)
})

test('expired Jarvis session recovers the same scope; a missing report requires explicit reselection', async ({ page }) => {
  const runs = (await (await page.request.get('/api/runs')).json()).runs
  const run = runs.find((r: { dataset_name: string }) => r.dataset_name === 'SYNTHETIC_maintenance_review.csv')
  await page.goto(`/#/dashboard/${run.id}/breakdown?by=Asset_ID`)
  const binding = page.waitForResponse(r => r.url().endsWith('/data-context') && r.request().method() === 'PUT')
  await page.getByRole('button', { name: 'Connect this view to Jarvis', exact: true }).click()
  const selected = await (await binding).json()
  await page.route(`**/api/sessions/${selected.session_id}`, route => route.fulfill({ status: 404, json: { detail: 'Session not found.' } }))
  const replacement = page.waitForResponse(r => r.url().endsWith('/data-context') && r.request().method() === 'PUT')
  await page.getByRole('button', { name: 'Refresh Jarvis scope' }).click()
  const next = await (await replacement).json()
  expect(next.session_id).not.toBe(selected.session_id)
  expect(next.data_context.run_id).toBe(run.id)
  expect(next.data_context.filters).toEqual(selected.data_context.filters)
  await page.route('**/data-context', route => route.request().method() === 'PUT'
    ? route.fulfill({ status: 404, json: { detail: 'Selected report unavailable.' } }) : route.continue())
  await page.getByRole('button', { name: 'Refresh Jarvis scope' }).click()
  await expect(page.getByRole('alert')).toContainText('selected report is no longer available')
  await expect(page.locator('.dash-jarvis__scope')).toContainText(run.id)
  await page.unroute('**/data-context')
  await page.getByRole('link', { name: 'Choose an available report' }).click()
  await page.getByRole('button').filter({ hasText: 'SYNTHETIC_maintenance_review.csv' }).click()
  await page.getByRole('button', { name: 'Connect this view to Jarvis', exact: true }).click()
  await page.getByRole('button', { name: 'What is total maintenance cost?', exact: true }).click()
  await page.getByRole('button', { name: 'Calculate from selected report', exact: true }).click()
  await expect(page.locator('.jarvis__evidence')).toContainText('Maintenance cost: 500')
  await page.locator('.jarvis-core').scrollIntoViewIfNeeded()
  await page.screenshot({ path: '../docs/screenshots/jarvis-recovered-scope.png' })
})
