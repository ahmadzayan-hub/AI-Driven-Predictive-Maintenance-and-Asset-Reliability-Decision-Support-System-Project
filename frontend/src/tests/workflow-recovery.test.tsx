import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ReadOnlyContext } from '../shared/readOnly'
import { RunsView } from '../features/runs/RunsView'
import { api, ApiError } from '../shared/api'
import { applyLocale } from '../i18n'
import { runFixture } from './run-fixture'
import { runStore } from '../features/runs/runStore'

beforeEach(() => {
  vi.stubGlobal('matchMedia', vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })))
  applyLocale('en')
  runStore.reset()
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [] })
  vi.spyOn(api, 'listDatasets').mockResolvedValue({ datasets: [] })
  vi.spyOn(api, 'pipelines').mockResolvedValue({ stages: [], profiles: {}, default: [], problems: [] })
  vi.spyOn(api, 'createRun').mockRejectedValue(new ApiError('Synthetic refusal'))
})
afterEach(() => { act(() => { applyLocale('en'); runStore.reset() }); vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('recoverable analysis navigation', () => {
  it('recovers failed history in Arabic without a run creation', async () => {
    applyLocale('ar')
    vi.mocked(api.listRuns).mockRejectedValueOnce(new Error('unavailable'))
    const user = userEvent.setup()
    render(<RunsView />)
    expect(await screen.findByText(/تعذّر تحديث التحليلات السابقة/)).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'إعادة محاولة تحميل التحليلات السابقة' }))
    expect(await screen.findByText('لم تُرجع الخدمة تحليلات سابقة لمساحة العمل هذه.')).toBeVisible()
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it('keeps demo browsing honest and shows failed opens without exposing write controls', async () => {
    const complete = runFixture({ state: 'completed' })
    vi.mocked(api.listRuns).mockResolvedValue({ runs: [complete] })
    vi.spyOn(api, 'getRun').mockRejectedValue(new ApiError('Synthetic run unavailable'))
    const user = userEvent.setup()
    render(<ReadOnlyContext.Provider value={true}><RunsView /></ReadOnlyContext.Provider>)
    expect(screen.getByRole('note')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Start run' })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: /Synthetic test analysis/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Synthetic run unavailable')
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it.each([
    { locale: 'en', source: 'Stored dataset', retry: 'Retry loading datasets', error: /Stored datasets could not be refreshed/, empty: /No stored datasets/ },
    { locale: 'ar', source: 'مجموعة بيانات مخزنة', retry: 'إعادة محاولة تحميل البيانات', error: /تعذّر تحديث مجموعات البيانات المحفوظة/, empty: /لا توجد بيانات محفوظة/ },
  ] as const)('distinguishes a failed dataset read from an empty list in $locale', async ({ locale, source, retry, error, empty }) => {
    applyLocale(locale)
    vi.mocked(api.listDatasets).mockRejectedValueOnce(new Error('private transport detail'))
      .mockResolvedValueOnce({ datasets: [{ id: 'synthetic-data', name: 'Synthetic fixture', created_at: '2026-10-23', sha256: 'fixture', byte_size: 20, row_count: 1, column_count: 2 }] })
    const user = userEvent.setup()
    render(<RunsView />)
    await user.click(screen.getByRole('button', { name: source }))
    expect(await screen.findByText(error)).toBeVisible()
    expect(screen.queryByText(empty)).not.toBeInTheDocument()
    expect(screen.queryByText('private transport detail')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: retry }))
    expect(await screen.findByRole('option', { name: /Synthetic fixture/ })).toBeVisible()
    expect(screen.queryByText(error)).not.toBeInTheDocument()
    expect(api.createRun).not.toHaveBeenCalled()
    expect(document.documentElement.dir).toBe(locale === 'ar' ? 'rtl' : 'ltr')
  })

  it('keeps a preset and edited question during failure and retries only the read', async () => {
    vi.mocked(api.listDatasets).mockRejectedValueOnce(new Error('unavailable')).mockResolvedValueOnce({ datasets: [] })
    const user = userEvent.setup()
    render(<RunsView preset={{ kind: 'stored', id: 'synthetic-data', name: 'Synthetic fixture' }} />)
    await user.clear(screen.getByLabelText('Goal'))
    await user.type(screen.getByLabelText('Goal'), 'Keep my question')
    expect(screen.getByRole('combobox', { name: 'Choose a stored dataset' })).toHaveValue('synthetic-data')
    await user.click(await screen.findByRole('button', { name: 'Retry loading datasets' }))
    await waitFor(() => expect(api.listDatasets).toHaveBeenCalledTimes(2))
    expect(screen.getByLabelText('Goal')).toHaveValue('Keep my question')
    expect(screen.getByRole('combobox', { name: 'Choose a stored dataset' })).toHaveValue('synthetic-data')
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it('announces loading rather than an empty history, then exposes a read-only retry', async () => {
    let fail!: (reason: Error) => void
    vi.mocked(api.listRuns).mockImplementationOnce(() => new Promise((_resolve, reject) => { fail = reject }))
    const user = userEvent.setup()
    render(<RunsView />)
    expect(screen.getByText('Loading previous runs…')).toBeVisible()
    expect(screen.queryByText('No previous runs were returned for this workspace.')).not.toBeInTheDocument()
    await act(async () => fail(new Error('unavailable')))
    const history = screen.getByRole('region', { name: 'Previous runs' })
    expect(within(history).getByRole('alert')).toHaveTextContent('Previous runs could not be refreshed')
    await user.click(within(history).getByRole('button', { name: 'Retry loading previous runs' }))
    expect(await screen.findByText('No previous runs were returned for this workspace.')).toBeVisible()
    expect(api.listRuns).toHaveBeenCalledTimes(2)
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it('ignores a late initial history response after creating a run', async () => {
    const complete = runFixture({ state: 'completed' })
    let finish!: (value: { runs: [] }) => void
    vi.mocked(api.listRuns).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
      .mockResolvedValueOnce({ runs: [complete] })
    vi.mocked(api.createRun).mockResolvedValue(complete)
    vi.spyOn(api, 'getRun').mockResolvedValue(complete)
    const user = userEvent.setup()
    render(<RunsView />)
    await user.click(screen.getByRole('button', { name: 'Start run' }))
    await waitFor(() => expect(api.listRuns).toHaveBeenCalledTimes(2))
    await act(async () => finish({ runs: [] }))
    await user.click(await screen.findByRole('button', { name: 'All runs' }))
    expect(screen.getByRole('region', { name: 'Previous runs' })).toHaveTextContent(complete.goal)
    expect(screen.queryByText('No previous runs were returned for this workspace.')).not.toBeInTheDocument()
  })

  it('retains known runs after a refresh fails and never labels them current', async () => {
    const complete = runFixture({ state: 'completed' })
    vi.mocked(api.listRuns).mockResolvedValueOnce({ runs: [complete] }).mockRejectedValueOnce(new Error('unavailable'))
    vi.mocked(api.createRun).mockResolvedValue(complete)
    vi.spyOn(api, 'getRun').mockResolvedValue(complete)
    const user = userEvent.setup()
    render(<RunsView />)
    await waitFor(() => expect(screen.getByRole('region', { name: 'Previous runs' })).toHaveTextContent(complete.goal))
    await user.click(screen.getByRole('button', { name: 'Start run' }))
    await user.click(await screen.findByRole('button', { name: 'All runs' }))
    const history = screen.getByRole('region', { name: 'Previous runs' })
    expect(within(history).getByRole('alert')).toHaveTextContent('last successful load')
    expect(history).toHaveTextContent(complete.goal)
    expect(api.createRun).toHaveBeenCalledTimes(1)
  })
})
