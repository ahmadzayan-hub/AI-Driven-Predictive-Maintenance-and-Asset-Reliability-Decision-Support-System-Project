import { expect, test } from '@playwright/test'
import { composerInput, expectModelUnavailable, lastAgentBubble, sendMessage, skipOnboarding } from './helpers'

// These tests inject transport failures; service-worker ownership must not bypass routing.
test.use({ serviceWorkers: 'block' })

test('session survives a page refresh', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/#/assistant')
  await expect(composerInput(page)).toBeVisible()

  await sendMessage(page, 'Keep this conversation across refreshes')
  await expect(lastAgentBubble(page)).toBeVisible()

  await page.reload()

  // The same transcript is restored instead of a fresh empty session.
  await expect(
    page.locator('.msg--user .msg__bubble', {
      hasText: 'Keep this conversation across refreshes',
    }),
  ).toBeVisible()
  await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
  await expect(composerInput(page)).toBeEnabled()
})

test('offline mode clears after a confirmed successful request', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/#/assistant')
  await expect(composerInput(page)).toBeVisible()

  // Simulate a dead backend: the send fails and the app reports offline.
  await page.route('**/api/**', (route) => route.abort())
  await sendMessage(page, 'This one fails')
  await expect(page.getByRole('status').filter({ hasText: 'Offline' })).toBeVisible()

  // Recovery checks the existing conversation without sending again. Only an
  // explicit manual-send choice may submit the retained draft after review.
  await page.unroute('**/api/**')
  let writes = 0
  page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/messages')) writes++ })
  await page.getByRole('button', { name: 'Check conversation', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('No message was resent')
  await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
  await expect(composerInput(page)).toHaveValue('This one fails')
  expect(writes).toBe(0)
  await page.getByRole('button', { name: 'Keep draft for manual send', exact: true }).click()
  await expectModelUnavailable(page, () => page.getByRole('button', { name: 'Send message', exact: true }).click())
  expect(writes).toBe(1)
  await expect(page.locator('.msg--user .msg__bubble').filter({ hasText: 'This one fails' })).toHaveCount(1)
})
