import { expect, test } from '@playwright/test'
import { randomUUID } from 'node:crypto'
import type { MessageResult } from '../src/shared/api'
import { lastAgentBubble, openTab, sendMessage, skipOnboarding } from './helpers'

// The chat understands plain language and acts on it: a sentence saves a
// memory, starts an analysis, or explains the latest report — and a
// sentence that would delete something is confirmed first.
test('plain language in the chat saves, analyses, explains, and confirms before deleting', async ({
  page,
}, testInfo) => {
  // A real pipeline sits between multiple conversation and memory actions;
  // its 40-second assertion must fit within the complete journey's budget.
  test.setTimeout(90_000)
  await skipOnboarding(page)
  await page.goto('/')

  // Projects share the local owner's memory. Identify this newly saved note
  // by its unique visible text; internal keys are no longer displayed.
  const memoryText = `the Q4 review is on Monday (${testInfo.project.name} ${randomUUID()})`
  const remember = `Remember that ${memoryText}`
  const savedResponse = page.waitForResponse((response) =>
    /\/api\/sessions\/[^/]+\/messages$/.test(response.url()) &&
    response.request().method() === 'POST' && response.request().postDataJSON()?.text === remember,
  )
  await sendMessage(page, remember)
  const saved = await (await savedResponse).json() as MessageResult
  const created = saved.state.memory_entries.filter((entry) => entry.text === memoryText)
  expect(created).toHaveLength(1)
  await expect(lastAgentBubble(page)).toHaveText('Information saved.')
  await sendMessage(page, 'What do you remember?')
  await expect(lastAgentBubble(page)).toContainText(memoryText)

  // Starting a run from the chat opens it: the person sees the pipeline
  // rather than being told where to find it.
  await sendMessage(page, 'Analyse the sample sales data')
  await expect(page.getByRole('region', { name: 'Approval required' })).toBeVisible({
    timeout: 40_000,
  })

  await openTab(page, /^Workspace/)
  await expect(lastAgentBubble(page)).toContainText('Started analysis')
  await sendMessage(page, 'What should we do?')
  await expect(lastAgentBubble(page)).toContainText('What should I do?')
  await expect(lastAgentBubble(page)).toContainText('The full report')

  // Deletion is never a single sentence away.
  await sendMessage(page, 'Forget everything')
  await expect(lastAgentBubble(page)).toContainText('Reply “yes” to confirm')
  await sendMessage(page, 'no')
  await expect(lastAgentBubble(page)).toHaveText('Nothing was changed.')
  await openTab(page, /^Memory/)
  const savedItem = page.locator('.memory__item').filter({ has: page.getByText(memoryText, { exact: true }) })
  await expect(savedItem).toBeVisible()
  await expect(savedItem.locator('.memory__text')).toHaveText(memoryText)

  await openTab(page, /^Workspace/)
  await sendMessage(page, 'Forget everything')
  // Wait for the question: the composer holds a message sent while the
  // previous one is still in flight, so an early "yes" would never go.
  await expect(lastAgentBubble(page)).toContainText('Reply “yes” to confirm')
  await sendMessage(page, 'yes')
  await expect(lastAgentBubble(page)).toHaveText('All saved information has been removed.')
})

