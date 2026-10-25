import { expect, test } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import type { MessageResult, OperationResult } from '../src/shared/api'
import { clickQuickAction, composerInput, lastAgentBubble, openTab, sendMessage, skipOnboarding } from './helpers'

test.describe('main user journey', () => {
  const consoleErrors: string[] = []

  test.beforeEach(async ({ page }) => {
    consoleErrors.length = 0
    page.on('console', (message) => {
      if (message.type() === 'error') consoleErrors.push(message.text())
    })
    page.on('pageerror', (error) => consoleErrors.push(String(error)))
    await skipOnboarding(page)
  })

  test('conversation, memory, preferences, history, and session lifecycle', async ({ page }, testInfo) => {
    // The full ten-step lifecycle completed its assertions in 36.5 seconds
    // on the Windows runner; preserve them under a scoped journey budget.
    test.setTimeout(60_000)
    // Projects share the owner's store. Count this journey's records and use
    // returned keys rather than assuming earlier tests emptied the account.
    const fixture = `${testInfo.project.name} ${randomUUID()}`
    const profileText = `My preferred language is English (${fixture})`
    const coffeeText = `Coffee at 8am (${fixture})`
    const editedCoffeeText = `Coffee at 7am sharp (${fixture})`
    const ownedItems = page.locator('.memory__item').filter({
      has: page.locator('.memory__text').filter({ hasText: fixture }),
    })
    // 1. Start the application and open a session.
    await page.goto('/#/assistant')
    await expect(page.getByRole('status').filter({ hasText: 'Ready' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Every asset. A clearer decision.' })).toBeVisible()

    // 2. Send a message.
    await sendMessage(page, 'Hello there')
    await expect(page.locator('.msg--user .msg__bubble').last()).toHaveText('Hello there')
    await expect(lastAgentBubble(page)).toContainText('Happy to help')

    // 3. Save a memory with a slash command.
    const remember = `/remember ${profileText}`
    const profileResponse = page.waitForResponse((response) =>
      /\/api\/sessions\/[^/]+\/messages$/.test(response.url()) &&
      response.request().method() === 'POST' && response.request().postDataJSON()?.text === remember,
    )
    await sendMessage(page, remember)
    const profileResult = await (await profileResponse).json() as MessageResult
    const profileEntries = profileResult.state.memory_entries.filter((entry) => entry.text === profileText)
    expect(profileEntries).toHaveLength(1)
    const profileItem = page.locator(`.memory__item[data-key="${profileEntries[0].key}"]`)
    await expect(lastAgentBubble(page)).toHaveText('Information saved.')

    // 4. Manage memory in the Memory panel: add, edit, export, delete.
    await openTab(page, /^Memory/)
    await expect(profileItem.locator('.memory__text')).toHaveText(profileText)

    await page.getByLabel('Information to remember').fill(coffeeText)
    await page.getByLabel('Category', { exact: true }).selectOption('work')
    const coffeeResponse = page.waitForResponse((response) =>
      /\/api\/sessions\/[^/]+\/memory$/.test(response.url()) &&
      response.request().method() === 'POST' && response.request().postDataJSON()?.information === coffeeText,
    )
    await page.getByRole('button', { name: 'Add memory' }).click()
    const coffeeResult = await (await coffeeResponse).json() as OperationResult
    const coffeeEntries = coffeeResult.state.memory_entries.filter((entry) => entry.text === coffeeText)
    expect(coffeeEntries).toHaveLength(1)
    const coffeeKey = coffeeEntries[0].key
    const coffeeItem = page.locator(`.memory__item[data-key="${coffeeKey}"]`)
    await expect(coffeeItem.locator('.memory__text')).toHaveText(coffeeText)
    await expect(ownedItems).toHaveCount(2)

    // Category filters narrow the list; All restores it.
    await page.getByRole('button', { name: 'Work', exact: true }).click()
    await expect(ownedItems).toHaveCount(1)
    await expect(profileItem).toHaveCount(0)
    await expect(coffeeItem.locator('.memory__text')).toHaveText(coffeeText)
    await page.getByRole('button', { name: 'All', exact: true }).click()
    await expect(ownedItems).toHaveCount(2)

    await coffeeItem.getByRole('button', { name: `Edit ${coffeeKey}`, exact: true }).click()
    await page.getByLabel(`Edit ${coffeeKey}`, { exact: true }).fill(editedCoffeeText)
    await page.getByRole('button', { name: 'Save', exact: true }).click()
    await expect(coffeeItem.locator('.memory__text')).toHaveText(editedCoffeeText)

    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /Export my data/ }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toBe('agentic-os-export.json')

    // Individual deletion is destructive and must be confirmed.
    await coffeeItem.getByRole('button', { name: `Forget ${coffeeKey}`, exact: true }).click()
    const confirmForget = page.getByRole('dialog', { name: `Forget ${coffeeKey}?` })
    await expect(confirmForget).toBeVisible()
    await confirmForget.getByRole('button', { name: 'Forget it' }).click()
    await expect(ownedItems).toHaveCount(1)
    await expect(coffeeItem).toHaveCount(0)
    await expect(profileItem.locator('.memory__text')).toHaveText(profileText)

    // 5. Change preferences and see them applied to replies.
    await openTab(page, /^Preferences/)
    await page.getByRole('button', { name: 'Concise' }).click()
    await expect(page.getByText('Preference updated: tone = concise.')).toBeVisible()

    await page.getByLabel('Your name').fill('Ahmad')
    await page.getByRole('button', { name: 'Save', exact: true }).first().click()
    await expect(page.getByText('Preference updated: user_name = Ahmad.')).toBeVisible()

    await openTab(page, /^Ask Miyaar/)
    // A sentence the assistant cannot act on gets an honest, tone-shaped
    // answer that says what can be asked — concise here.
    await sendMessage(page, 'Ping')
    await expect(lastAgentBubble(page)).toContainText('Not sure what to do with “Ping”')

    // 6. View history.
    await sendMessage(page, '/history')
    await expect(lastAgentBubble(page)).toContainText('Hello there')
    await expect(lastAgentBubble(page)).toContainText('Ping')

    // 7. Clear history with confirmation (from Memory > Data controls).
    await openTab(page, /^Memory/)
    await page.getByRole('button', { name: /Clear conversation history/ }).click()
    const confirmClear = page.getByRole('dialog', { name: 'Clear conversation history?' })
    await expect(confirmClear).toBeVisible()
    await confirmClear.getByRole('button', { name: 'Clear history' }).click()
    await expect(confirmClear).toBeHidden()

    await openTab(page, /^Ask Miyaar/)
    await sendMessage(page, '/history')
    await expect(lastAgentBubble(page)).toHaveText('No conversation history is available.')

    // 8. Delete all memory with confirmation (also resets shared e2e state).
    await openTab(page, /^Memory/)
    await page.getByRole('button', { name: /Delete all memory/ }).click()
    const confirmMemory = page.getByRole('dialog', { name: 'Delete all memory?' })
    await confirmMemory.getByRole('button', { name: 'Delete all memory' }).click()
    await expect(page.getByText('Nothing saved yet.', { exact: false })).toBeVisible()

    // 9. End the session gracefully, then start a new one.
    await clickQuickAction(page, /^End session/)
    const confirmEnd = page.getByRole('dialog', { name: 'End this session?' })
    await confirmEnd.getByRole('button', { name: 'End session' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'Session ended' })).toBeVisible()

    await openTab(page, /^Ask Miyaar/)
    await expect(page.getByText('This session has ended.', { exact: false }).first()).toBeVisible()
    await expect(composerInput(page)).toBeDisabled()

    await clickQuickAction(page, /^New session/)
    await expect(composerInput(page)).toBeEnabled()
    await expect(page.getByRole('heading', { name: 'Every asset. A clearer decision.' })).toBeVisible()

    // 10. The whole journey must produce no browser console errors.
    expect(consoleErrors).toEqual([])
  })

  test('command palette inserts commands and unknown commands fail gracefully', async ({ page }) => {
    await page.goto('/#/assistant')
    await expect(composerInput(page)).toBeVisible()

    await page.keyboard.press('ControlOrMeta+k')
    const palette = page.getByRole('dialog', { name: 'Command palette' })
    await expect(palette).toBeVisible()
    await page.keyboard.type('help')
    await page.keyboard.press('Enter')
    await expect(palette).toBeHidden()

    const input = composerInput(page)
    await expect(input).toHaveValue('/help')
    await input.press('Enter')
    await expect(lastAgentBubble(page)).toContainText('Available commands:')

    await sendMessage(page, '/teleport')
    await expect(lastAgentBubble(page)).toContainText('Unknown command: /teleport')
    expect(consoleErrors).toEqual([])
  })

  test('layout has no horizontal overflow', async ({ page }) => {
    await page.goto('/#/assistant')
    await expect(composerInput(page)).toBeVisible()
    await sendMessage(page, 'A fairly long message that should wrap correctly on small screens without causing any horizontal scrolling anywhere in the layout.')
    await expect(lastAgentBubble(page)).toBeVisible()

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    expect(overflow).toBeLessThanOrEqual(0)
  })
})

