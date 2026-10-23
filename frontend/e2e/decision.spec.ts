import { expect, test } from '@playwright/test'
import { openTab, skipOnboarding } from './helpers'

// The interface half of assessment findings A2 and A13: the analyst states
// an improvement and a cost per group before the run, the report scores
// every option on them and says which were stated, and the decision
// record on the run shows the inputs, the flip point and who decided.
test('stated improvement and cost reach the decision record, which the approval completes', async ({ page }) => {
  await skipOnboarding(page)
  await page.goto('/')
  await openTab(page, /^Analyses/)

  await page.getByText('Improvement and cost (optional)').click()
  const first = page.getByRole('group', { name: 'Group 1' })
  await first.getByLabel('Group, as the data spells it').fill('South')
  await first.getByLabel('Improvement, %').fill('15')
  await first.getByLabel('Cost, in the measure’s units').fill('1000')
  await page.getByRole('button', { name: 'Add a group' }).click()
  const second = page.getByRole('group', { name: 'Group 2' })
  await second.getByLabel('Group, as the data spells it').fill('North')
  await second.getByLabel('Cost, in the measure’s units').fill('2000')
  await page.getByRole('button', { name: 'Start run' }).click()

  const approval = page.getByRole('region', { name: 'Approval required' })
  await expect(approval).toBeVisible({ timeout: 40_000 })
  const record = page.getByRole('region', { name: 'Decision record' })
  await expect(record).toBeVisible()
  await expect(record).toContainText('Awaiting the approver.')
  // South's improvement was stated; the rest keep the assumed 10%.
  const south = record.getByRole('row', { name: /South/ }).first()
  await expect(south).toContainText('15%')
  await expect(south).toContainText('stated')
  await expect(record.getByText('assumed').first()).toBeVisible()
  await expect(record.getByText(/decision\./)).toHaveCount(0)

  // The same record in Arabic, with the audited English kept for the data.
  await page.getByRole('button', { name: 'Change language' }).click()
  await expect(page.getByRole('heading', { name: 'سجل القرار' })).toBeVisible()
  await page.getByRole('button', { name: 'تغيير اللغة' }).click()

  await approval.getByText('Review the exact report').click()
  await approval.getByLabel('I have read this exact report').check()
  await approval.getByRole('button', { name: 'Approve and publish' }).click()
  await expect(page.getByText('state: completed')).toBeVisible()
  await expect(record).toContainText(/Approved (by .+ )?on /)
})
