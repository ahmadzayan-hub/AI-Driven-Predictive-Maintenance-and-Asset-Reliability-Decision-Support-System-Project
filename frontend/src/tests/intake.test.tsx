import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { RunsView } from '../features/runs/RunsView'
import { api, ApiError, MAX_UPLOAD_BYTES } from '../shared/api'
import { applyLocale } from '../i18n'
import type { UploadResult } from '../shared/types'

const upload: UploadResult = {
  dataset: { id: 'equipment1', name: 'equipment.xlsx', sha256: 'fixture-hash', byte_size: 80, created_at: '2026-10-17', row_count: 2, column_count: 2, source_format: 'xlsx' },
  columns: ['plant', 'cost'], preview: [['North', '320'], ['South', '180']],
  created: true, warnings: [], sheets: ['Equipment', 'Costs'], selected_sheet: 'Equipment',
}

beforeEach(() => {
  applyLocale('en')
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [] })
  vi.spyOn(api, 'listDatasets').mockResolvedValue({ datasets: [] })
  vi.spyOn(api, 'pipelines').mockResolvedValue({ stages: [], profiles: {}, default: [], problems: [] })
  vi.spyOn(api, 'createRun').mockRejectedValue(new ApiError('Test stopped after validating request'))
})
afterEach(() => {
  act(() => applyLocale('en'))
  sessionStorage.clear()
  vi.restoreAllMocks()
})

describe('real data intake', () => {
  it('uses Arabic custom stage names in the profile help and execution plan', async () => {
    applyLocale('ar')
    vi.mocked(api.pipelines).mockResolvedValue({
      stages: [{ role: 'rail_asset_manager', title: 'English railway title', title_ar: 'وكيل أصول السكك', after: 'cleaner', question: null, can_fail_run: false }],
      profiles: { maintenance: ['rail_asset_manager'] }, default: [], problems: [],
    })
    render(<RunsView preset={{ kind: 'upload', profile: 'maintenance' }} />)
    await waitFor(() => expect(screen.getAllByText(/وكيل أصول السكك/)).toHaveLength(2))
    expect(screen.queryByText(/English railway title/)).not.toBeInTheDocument()
  })
  it('blocks empty upload and stored submissions instead of running sample data', async () => {
    const user = userEvent.setup()
    render(<RunsView preset={{ kind: 'upload' }} />)
    const start = screen.getByRole('button', { name: 'Start run' })
    expect(start).toBeDisabled()
    fireEvent.submit(start.closest('form')!)
    expect(api.createRun).not.toHaveBeenCalled()
    expect(screen.getByText('Upload a file, paste CSV, or choose a stored dataset before starting.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Stored dataset' }))
    fireEvent.submit(start.closest('form')!)
    expect(api.createRun).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Sample sales data' }))
    expect(start).toBeEnabled()
  })

  it('waits for the upload and analyzes only the returned dataset id', async () => {
    const user = userEvent.setup()
    let finish!: (value: UploadResult) => void
    vi.spyOn(api, 'uploadDataset').mockImplementation(() => new Promise((resolve) => { finish = resolve }))
    render(<RunsView preset={{ kind: 'upload' }} />)
    const file = new File(['synthetic fixture'], 'equipment.xlsx')
    await user.upload(screen.getByLabelText('Choose a file'), file)
    const start = screen.getByRole('button', { name: 'Start run' })
    expect(start).toBeDisabled()
    fireEvent.submit(start.closest('form')!)
    expect(api.createRun).not.toHaveBeenCalled()
    await act(async () => finish(upload))
    await user.click(start)
    await waitFor(() => expect(api.createRun).toHaveBeenCalledTimes(1))
    expect(vi.mocked(api.createRun).mock.calls[0]).toEqual([
      'Analyse equipment.xlsx and produce a business report', undefined, undefined, undefined, 'en', 'equipment1', undefined,
    ])
  })

  it('re-uploads the same workbook with the chosen sheet and clears stale data on failure', async () => {
    const user = userEvent.setup()
    const uploader = vi.spyOn(api, 'uploadDataset').mockResolvedValueOnce(upload).mockRejectedValueOnce(new ApiError('Sheet has no data'))
    render(<RunsView preset={{ kind: 'upload' }} />)
    const file = new File(['synthetic workbook'], 'equipment.xlsx')
    await user.upload(screen.getByLabelText('Choose a file'), file)
    await user.selectOptions(await screen.findByRole('combobox', { name: 'Workbook sheet' }), 'Costs')
    expect(uploader).toHaveBeenLastCalledWith(file, 'en', 'Costs')
    expect(await screen.findByText('Sheet has no data')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Start run' })).toBeDisabled()
    expect(api.createRun).not.toHaveBeenCalled()
  })

  it('rejects an oversized replacement rather than analyzing an older file or pasted data', async () => {
    const user = userEvent.setup()
    const uploader = vi.spyOn(api, 'uploadDataset').mockResolvedValue(upload)
    render(<RunsView preset={{ kind: 'upload' }} />)
    await user.upload(screen.getByLabelText('Choose a file'), new File(['fixture'], 'equipment.xlsx'))
    const file = new File(['x'], 'large.csv')
    Object.defineProperty(file, 'size', { value: MAX_UPLOAD_BYTES + 1 })
    await user.upload(screen.getByLabelText('Choose a file'), file)
    expect(uploader).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('button', { name: 'Start run' })).toBeDisabled()
    expect(screen.getByText(/large.csv is/)).toBeVisible()
  })

  it('accepts pasted CSV in Arabic without silently choosing a sample', async () => {
    const user = userEvent.setup()
    applyLocale('ar')
    render(<RunsView preset={{ kind: 'upload' }} />)
    const csv = 'plant,cost\nNorth,320\nSouth,180'
    fireEvent.change(screen.getByRole('textbox', { name: /CSV/ }), { target: { value: csv } })
    fireEvent.submit(screen.getByLabelText('الهدف').closest('form')!)
    await waitFor(() => expect(api.createRun).toHaveBeenCalled())
    expect(vi.mocked(api.createRun).mock.calls[0][1]).toBe(csv)
    expect(vi.mocked(api.createRun).mock.calls[0][4]).toBe('ar')
    // Returning to a file upload clears that paste before the request starts.
    const uploader = vi.spyOn(api, 'uploadDataset').mockRejectedValue(new ApiError('Unreadable file'))
    const input = document.querySelector<HTMLInputElement>('input[type="file"]')!
    await user.upload(input, new File(['bad'], 'broken.csv'))
    expect(uploader).toHaveBeenCalled()
    expect(screen.getByRole('textbox', { name: /CSV/ })).toHaveValue('')
  })
})
