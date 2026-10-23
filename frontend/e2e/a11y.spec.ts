import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import { openTab, sendMessage, skipOnboarding } from './helpers'

// Scanning with reduced motion enabled avoids analyzing dialogs mid-fade
// (axe would read blended colors) and exercises the app's
// prefers-reduced-motion support at the same time.
test.use({ contextOptions: { reducedMotion: 'reduce' } })

// Automated WCAG 2.x A/AA scan of every view and the dialogs. Automated
// checks complement — not replace — the manual keyboard review recorded in
// docs/UI_UX_AUDIT.md.
async function expectNoViolations(page: import('@playwright/test').Page, context: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(
    results.violations,
    `${context}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`,
  ).toEqual([])
}

test('all views and dialogs pass automated WCAG 2.2 AA checks', async ({ page }) => {
  // Ten sequential full-page audits plus a real pipeline and mobile
  // navigation need a journey budget; individual waits and audit rules stay.
  test.setTimeout(120_000)
  await skipOnboarding(page)
  // The app lands on the Command Centre (finding U12); the chat is scanned first.
  await page.goto('/#/assistant')

  await sendMessage(page, 'Hello there')
  await page.locator('.msg--agent .msg__bubble').last().waitFor()
  await expectNoViolations(page, 'chat view')

  await openTab(page, /^Memory/)
  await expectNoViolations(page, 'memory view')

  await openTab(page, /^Preferences/)
  await expectNoViolations(page, 'preferences view')

  await openTab(page, /^Activity/)
  await expectNoViolations(page, 'activity view')

  // The Runs view is the most complex screen in the app — approval card,
  // charts, and the analytics-type tablist — so it is scanned in the
  // state that has all of them on screen at once.
  await openTab(page, /^Analytics/)
  await expectNoViolations(page, 'runs view (setup)')
  await page.getByRole('button', { name: 'Start run' }).click()
  await expect(page.getByRole('region', { name: 'Approval required' })).toBeVisible({
    timeout: 40_000,
  })
  await expectNoViolations(page, 'runs view (approval, charts, reports)')

  // Asset Intelligence reads the latest maintenance evidence; with the
  // sample run it shows the "no validated analysis" state and the figures
  // legend (assessment finding U13: every navigation view is scanned).
  await openTab(page, /^Asset/)
  await expect(page.getByRole('heading', { name: 'Asset Intelligence', level: 2 })).toBeVisible()
  await expect(page.locator('main .skeleton:visible')).toHaveCount(0)
  await expectNoViolations(page, 'asset intelligence view')

  // The approval inbox, with the run above waiting in it and its card open:
  // the exact report, the facts and the read-before-approve gate.
  await openTab(page, /^Approvals/)
  await expect(page.getByRole('heading', { name: 'Approval inbox', level: 2 })).toBeVisible()
  await page.getByRole('button', { name: 'Review', exact: true }).first().click()
  await expect(page.getByRole('region', { name: 'Approval required' })).toBeVisible()
  await expectNoViolations(page, 'approvals view (run waiting, card open)')

  await page.keyboard.press('ControlOrMeta+k')
  await page.getByRole('dialog', { name: 'Command palette' }).waitFor()
  await expectNoViolations(page, 'command palette')
  await page.keyboard.press('Escape')

  await openTab(page, /^Help and commands$/)
  await page.getByRole('dialog', { name: 'Commands' }).waitFor()
  await expectNoViolations(page, 'help dialog')
})

test('onboarding dialog passes automated WCAG 2.2 AA checks', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('dialog', { name: 'Welcome to Asset Reliability' }).waitFor()
  await expectNoViolations(page, 'onboarding dialog')
})
