import { expect, test } from '@playwright/test'
import { composerInput, lastAgentBubble, openTab, sendMessage, skipOnboarding } from './helpers'

// The journey specs already cover 375 px and 1440 px; this checks the
// remaining required breakpoints.
const WIDTHS = [
  { width: 320, height: 640 },
  { width: 768, height: 1024 },
  { width: 1024, height: 768 },
]

async function horizontalOverflow(page: import('@playwright/test').Page) {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )
}

test('no horizontal overflow at 320, 768, and 1024 px', async ({ page }) => {
  test.skip(test.info().project.name !== 'desktop', 'viewport-resize test runs once')
  // A real run puts a card in the approval inbox, so the check reads the
  // views with content, not their empty states (assessment finding U13).
  test.setTimeout(90_000)
  await skipOnboarding(page)
  await page.goto('/#/assistant')
  await sendMessage(
    page,
    'A long message with an unbreakable token Supercalifragilisticexpialidocious1234567890 to prove wrapping works.',
  )
  await expect(lastAgentBubble(page)).toBeVisible()
  await openTab(page, /^Analyses/)
  await page.getByRole('button', { name: 'Start run' }).click()
  await expect(page.getByRole('region', { name: 'Approval required' })).toBeVisible({
    timeout: 40_000,
  })

  for (const viewport of WIDTHS) {
    await page.setViewportSize(viewport)

    await openTab(page, /^Workspace/)
    await expect(composerInput(page)).toBeVisible()
    expect(await horizontalOverflow(page), `overflow at ${viewport.width}px (workspace)`).toBeLessThanOrEqual(0)

    await openTab(page, /^Asset/)
    await expect(page.getByRole('heading', { name: 'Asset Intelligence', level: 2 })).toBeVisible()
    await expect(page.locator('main .skeleton:visible')).toHaveCount(0)
    expect(await horizontalOverflow(page), `overflow at ${viewport.width}px (assets)`).toBeLessThanOrEqual(0)

    await openTab(page, /^Approvals/)
    await expect(page.getByRole('heading', { name: 'Approval inbox', level: 2 })).toBeVisible()
    await expect(page.locator('.approval-inbox .card').first()).toBeVisible()
    expect(await horizontalOverflow(page), `overflow at ${viewport.width}px (approvals)`).toBeLessThanOrEqual(0)
  }
})
