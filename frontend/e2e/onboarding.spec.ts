import { expect, test } from '@playwright/test'

test('first visit shows dismissible onboarding that never returns', async ({ page }) => {
  await page.goto('/')

  const dialog = page.getByRole('dialog', { name: 'Welcome to Asset Reliability' })
  await expect(dialog).toBeVisible()
  await expect(dialog).toContainText('Memory is stored locally')

  await dialog.getByRole('button', { name: 'Get started' }).click()
  await expect(dialog).toBeHidden()

  await page.reload()
  // The app lands on the Command Centre (finding U12), with no dialog again.
  await expect(page.getByRole('heading', { name: 'Command Centre', level: 2 })).toBeVisible()
  await expect(page.getByRole('dialog', { name: 'Welcome to Asset Reliability' })).toBeHidden()
})
