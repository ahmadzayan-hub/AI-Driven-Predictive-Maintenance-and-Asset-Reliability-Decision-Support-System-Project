import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'
import { openTab, viewLoaded } from './helpers'

// The view-only demo (ADR 2026-10-21): the third web server runs with
// AGENTIC_OS_DEMO=1 on port 8125. No sign-in, one seeded fictional
// analysis, nothing writable; the controls that would write are replaced
// by a note, not left to fail (assessment finding U13).

const GOAL = 'Review fleet maintenance performance for 2025 (fictional demo data)'
const DEMO_NOTE =
  'A view-only demo on fictional data. There is no sign-in, and nothing can be uploaded, changed or approved here.'
const DEMO_NOTE_AR =
  'عرض تجريبي للاطلاع فقط على بيانات افتراضية. لا يوجد تسجيل دخول، ولا يمكن رفع أي ملف أو تعديله أو اعتماده هنا.'

test.use({ baseURL: 'http://127.0.0.1:8125', contextOptions: { reducedMotion: 'reduce' } })

async function expectNoViolations(page: Page, context: string) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(
    results.violations,
    `${context}: ${results.violations.map((v) => `${v.id} (${v.nodes.length})`).join(', ')}`,
  ).toEqual([])
}

/** The Command Centre with its decision brief loaded, not its skeleton. */
async function commandCentreReady(page: Page) {
  await expect(page.getByRole('heading', { name: 'Command Centre', level: 2 })).toBeVisible()
  await expect(page.locator('.command--pending')).toHaveCount(0)
  await expect(page.locator('main .skeleton:visible')).toHaveCount(0)
}

test('opens on the Command Centre without sign-in and shows the seeded fictional analysis', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', (error) => pageErrors.push(String(error)))
  const failed: string[] = []
  page.on('response', (response) => {
    if (response.status() >= 400) failed.push(`${response.status()} ${response.url()}`)
  })

  await page.goto('/')
  await viewLoaded(page)
  // No sign-in page, no first-run dialog, no chat session: a visitor lands
  // on the Command Centre as the demo visitor.
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await commandCentreReady(page)
  await expect(page.getByText('View-only demo')).toBeVisible()
  // The visitor's name is in the sidebar, which phones fold into the drawer.
  await expect(page.getByText('Demo visitor')).toHaveCount(1)
  await expect(page.getByRole('textbox', { name: 'Message' })).toHaveCount(0)

  // The seeded analysis waits at the gate and is the brief on screen.
  await expect(page.locator('.kpi--attention')).toContainText('Waiting for approval')
  await expect(page.getByRole('region', { name: 'Executive decision intelligence' })).toBeVisible()
  await expect(page.getByText(GOAL).first()).toBeVisible()
  // Nothing that would start an analysis is offered.
  for (const name of ['Start an analysis', 'Try the sample data', 'Add a dataset', 'Analyze a dataset']) {
    await expect(page.getByRole('button', { name })).toHaveCount(0)
  }
  await expectNoViolations(page, 'command centre (demo)')

  // The executive overview renders from the seeded run.
  await page.getByRole('button', { name: 'Open the executive overview' }).click()
  await viewLoaded(page)
  await expect(page.getByRole('heading', { name: 'Executive overview', exact: true })).toBeVisible()
  await expect(page.locator('main .skeleton:visible')).toHaveCount(0)

  // A link to a view the demo does not have lands on the Command Centre.
  await page.goto('/#/chat')
  await viewLoaded(page)
  await expect(page.getByRole('heading', { name: 'Command Centre', level: 2 })).toBeVisible()

  expect(pageErrors).toEqual([])
  expect(failed).toEqual([])
})

test('upload, approve and assistant controls say the demo is view-only instead of failing', async ({ page }) => {
  await page.goto('/')
  await viewLoaded(page)
  await commandCentreReady(page)

  // The assistant lives on a chat session, which the demo never opens.
  await expect(page.locator('.miyaar-sidebar')).toHaveCount(0)
  await expect(page.getByRole('button', { name: /^Workspace/ })).toHaveCount(0)
  // The header badge carries the note for anyone who hovers it.
  await expect(page.getByText('View-only demo')).toHaveAttribute('title', DEMO_NOTE)

  // Asset Intelligence reads the seeded maintenance run and offers no upload.
  await openTab(page, /^Asset/)
  await expect(page.getByRole('heading', { name: 'Asset Intelligence', level: 2 })).toBeVisible()
  await expect(page.locator('main .skeleton:visible')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Analyze railway data' })).toHaveCount(0)
  await expect(page.locator('.asset-intelligence__source')).toContainText('demo-fleet-fictional.csv')

  // Datasets lists the one fictional file with nothing to add or analyse.
  await openTab(page, /^Datasets/)
  await expect(page.getByRole('heading', { name: 'Datasets', level: 2 })).toBeVisible()
  await expect(page.locator('.dataset__name').filter({ hasText: 'demo-fleet-fictional.csv' })).toHaveCount(1)
  await expect(page.getByRole('button', { name: 'Add a dataset' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: /^Analyse / })).toHaveCount(0)

  // The run view: the approval card explains instead of offering a decision,
  // and the run cannot be paused or cancelled.
  await openTab(page, /^Command Centre/)
  await commandCentreReady(page)
  await page.getByRole('button', { name: /Review$/ }).first().click()
  await viewLoaded(page)
  const card = page.getByRole('region', { name: 'Approval required' })
  await expect(card).toBeVisible()
  await expect(page.getByText('state: awaiting approval')).toBeVisible()
  await expect(card).toContainText(DEMO_NOTE)
  for (const name of ['Approve and publish', 'Reject', 'Pause', 'Cancel']) {
    await expect(page.getByRole('button', { name, exact: true })).toHaveCount(0)
  }
  await expect(page.getByRole('checkbox', { name: 'I have read this exact report' })).toHaveCount(0)
  await expectNoViolations(page, 'run view (demo)')

  // The approval inbox says the same when the card is opened there.
  await openTab(page, /^Approvals/)
  await expect(page.getByRole('heading', { name: 'Approval inbox', level: 2 })).toBeVisible()
  await page.getByRole('button', { name: 'Review', exact: true }).first().click()
  await expect(page.getByRole('region', { name: 'Approval required' })).toContainText(DEMO_NOTE)
  await expect(page.getByRole('button', { name: 'Approve and publish', exact: true })).toHaveCount(0)
})

test('the demo reads in Arabic, right-to-left, with the same note', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('aos-locale', 'ar'))
  await page.goto('/')
  await viewLoaded(page)
  await expect(page.locator('html')).toHaveAttribute('dir', 'rtl')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: 'مركز القيادة', level: 2 })).toBeVisible()
  await expect(page.getByText('عرض تجريبي للاطلاع فقط')).toBeVisible()
  await expect(page.getByText('زائر العرض التجريبي')).toHaveCount(1)
  await expect(page.locator('.command--pending')).toHaveCount(0)
  await expect(page.locator('main .skeleton:visible')).toHaveCount(0)
  await expectNoViolations(page, 'command centre (demo, ar)')

  // The approval inbox, through the drawer on a phone.
  await openTab(page, /^الموافقات/, 'ar')
  await expect(page.getByRole('heading', { name: 'صندوق الموافقات', level: 2 })).toBeVisible()
  await page.getByRole('button', { name: 'راجِع', exact: true }).first().click()
  const card = page.getByRole('region', { name: 'موافقة مطلوبة' })
  await expect(card).toBeVisible()
  await expect(card).toContainText(DEMO_NOTE_AR)
  await expect(page.getByRole('button', { name: 'الموافقة والنشر', exact: true })).toHaveCount(0)
  // When something scrolls sideways, name it: the hosted runner's Arabic
  // fonts differ from a laptop's, and a bare "1" explains nothing.
  const overflow = await page.evaluate(() => {
    const root = document.documentElement
    const spill = root.scrollWidth - root.clientWidth
    if (spill <= 0) return { spill, culprits: [] as string[] }
    const culprits: string[] = []
    for (const element of Array.from(document.body.querySelectorAll<HTMLElement>('*'))) {
      const box = element.getBoundingClientRect()
      if (box.width === 0) continue
      if (box.right > root.clientWidth + 0.5 || box.left < -0.5) {
        const label = `${element.tagName.toLowerCase()}${element.className ? '.' + String(element.className).split(' ').join('.') : ''}`
        culprits.push(`${label} [${Math.round(box.left)}..${Math.round(box.right)}] ${(element.textContent ?? '').trim().slice(0, 40)}`)
      }
      if (culprits.length >= 8) break
    }
    return { spill, culprits }
  })
  expect(overflow.spill, overflow.culprits.join('\n')).toBeLessThanOrEqual(0)
  await expectNoViolations(page, 'approval inbox (demo, ar)')
})
