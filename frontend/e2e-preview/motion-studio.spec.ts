import { expect, test } from '@playwright/test'

test('motion studio is responsive and does not invent live figures', async ({ page }) => {
  await page.goto('/motion-studio/index.html')
  await expect(page.locator('#screen')).toBeVisible()
  await expect(page.locator('#status')).toContainText('Illustrative draft')
  await page.locator('#lang').selectOption('en')
  await page.locator('#format').selectOption('vertical')
  await expect(page.locator('#screen')).toHaveAttribute('height', '1280')
})

test('source import requires traceable evidence before export', async ({ page }) => {
  await page.goto('/motion-studio/index.html')
  await page.locator('#exportEvidence').click()
  await expect(page.locator('#status')).toContainText('Cannot export')
  const evidence = {
    schema: 'motion-evidence-v1', language: 'en', format: 'wide',
    classification: 'INTERNAL', duration: 10,
    scenes: ['hook', 'evidence', 'action'].map(kind => ({
      kind, text: 'Fixture statement',
      evidence: [{source_id: 'run-1', revision: 'v1', locator: 'report:2',
        data_status: 'RECORDED_IN_REGISTER'}],
    })),
  }
  await page.locator('#evidenceFile').setInputFiles({
    name: 'source.json', mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(evidence)),
  })
  await expect(page.locator('#status')).toContainText('loaded')
  await expect(page.locator('#headline')).toHaveValue('Fixture statement')
})
