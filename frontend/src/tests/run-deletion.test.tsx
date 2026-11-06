import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { RunsView } from '../features/runs/RunsView'
import { runStore } from '../features/runs/runStore'
import { applyLocale } from '../i18n'
import { api } from '../shared/api'
import { ReadOnlyContext } from '../shared/readOnly'
import { runFixture } from './run-fixture'

// Deleting an analysis (docs/adr/2026-11-06-delete-a-run-keep-its-audit.md): confirmed first,
// datasets only when asked, the run leaves the list. Synthetic fixture only.
beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
  applyLocale('en')
  runStore.reset()
  vi.spyOn(api, 'listDatasets').mockResolvedValue({ datasets: [] })
  vi.spyOn(api, 'pipelines').mockResolvedValue({ stages: [], profiles: {}, default: [], problems: [] })
})
afterEach(() => { act(() => { applyLocale('en'); runStore.reset() }); vi.restoreAllMocks(); vi.unstubAllGlobals() })

it.each(['en', 'ar'] as const)('deletes an analysis only after confirming, with its datasets when asked (%s)', async (locale) => {
  applyLocale(locale)
  const complete = runFixture({ state: 'completed' })
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [complete] })
  vi.spyOn(api, 'getRun').mockResolvedValue(complete)
  const remove = vi.spyOn(api, 'deleteRun').mockResolvedValue({ deleted: complete.id, datasets_deleted: [], datasets_kept: [], audit_kept: 2 })
  const user = userEvent.setup()
  render(<RunsView openRunId={complete.id} />)
  const label = locale === 'ar' ? 'حذف التحليل' : 'Delete analysis'
  await user.click(await screen.findByRole('button', { name: label }))
  expect(remove).not.toHaveBeenCalled()
  await user.click(screen.getByRole('checkbox', { name: locale === 'ar' ? 'احذف أيضاً مجموعات البيانات التي لا يقرؤها تحليل آخر' : 'Also delete the datasets no other analysis reads' }))
  const dialog = screen.getByRole('dialog')
  await user.click(dialog.querySelector('.btn--danger')!)
  await waitFor(() => expect(remove).toHaveBeenCalledWith(complete.id, true, locale))
  expect(await screen.findByRole('region', { name: locale === 'ar' ? 'التحليلات السابقة' : 'Previous runs' })).not.toHaveTextContent(complete.goal)
})

it('offers no delete in the read-only demo', async () => {
  const complete = runFixture({ state: 'completed' })
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [complete] })
  vi.spyOn(api, 'getRun').mockResolvedValue(complete)
  render(<ReadOnlyContext.Provider value={true}><RunsView openRunId={complete.id} /></ReadOnlyContext.Provider>)
  await screen.findByRole('button', { name: 'All runs' })
  expect(screen.queryByRole('button', { name: 'Delete analysis' })).toBeNull()
})
