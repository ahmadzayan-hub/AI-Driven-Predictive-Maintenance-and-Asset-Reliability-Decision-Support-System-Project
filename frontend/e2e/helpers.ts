import { expect } from '@playwright/test'
import type { Page } from '@playwright/test'

/** Skip the first-run onboarding dialog for tests that don't cover it. */
export async function skipOnboarding(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem('aos-onboarded', '1')
  })
}

/** Wait for rendered navigation, including the asynchronously loaded drawer. */
export async function revealNavigation(page: Page, language: 'en' | 'ar' = 'en') {
  const menu = page.getByRole('button', { name: language === 'ar' ? 'فتح قائمة التنقل' : 'Open navigation' })
  const groups = page.locator('.sidebar__group').filter({ visible: true })
  await menu.or(groups.first()).first().waitFor()
  if (!(await groups.first().isVisible())) await menu.click()
  await groups.first().waitFor()
  return groups
}

/** Open a preserved route through its actual responsive disclosure controls. */
export async function openTab(page: Page, name: RegExp, language: 'en' | 'ar' = 'en') {
  const groups = await revealNavigation(page, language)
  const target = page.getByRole('button', { name }).filter({ visible: true })
  const group = groups.filter({ has: page.getByRole('button', { name, includeHidden: true }) }).first()
  if (await group.count() && !(await group.evaluate((element) => (element as HTMLDetailsElement).open))) await group.locator('summary').click()
  await target.first().click()
  await viewLoaded(page)
}

/** Wait until the view's chunk has arrived (ADR 0028), so a check reads
 *  the view and not its loading skeleton. */
export async function viewLoaded(page: Page) {
  // Two panes can be loading at once (the Command Centre the app lands on
  // and the view just opened), so wait for every placeholder, not one.
  await expect(page.locator('.viewload')).toHaveCount(0)
}

/** Click a sidebar quick action (New session / Clear history / End session),
 *  going through the drawer on mobile viewports. */
export async function clickQuickAction(page: Page, name: RegExp) {
  await openTab(page, name)
}

/** The composer's message textbox. */
export function composerInput(page: Page) {
  return page.getByRole('textbox', { name: 'Message' })
}

/** Send a message through the composer and wait for the agent's reply. */
export async function sendMessage(page: Page, text: string) {
  const input = composerInput(page)
  await input.click()
  await input.fill(text)
  await input.press('Enter')
}

export function lastAgentBubble(page: Page) {
  return page.locator('.msg--agent .msg__bubble').last()
}

/** Phones fold the dashboard filters away until asked; desktop shows them open. */
export async function openFilters(page: Page) {
  const fold = page.locator('.dash-filters > details')
  if (!(await fold.evaluate((element) => (element as HTMLDetailsElement).open))) await fold.locator('summary').first().click()
}
