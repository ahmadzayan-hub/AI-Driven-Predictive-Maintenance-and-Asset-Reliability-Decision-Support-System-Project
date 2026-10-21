import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { DatasetsView } from '../features/datasets/DatasetsView'
import { ReadOnlyContext } from '../shared/readOnly'
import { OverviewView } from '../features/overview/OverviewView'
import { ConnectorsPanel } from '../features/live/ConnectorsPanel'
import { connectorsApi } from '../features/live/connectors'
import type { Connector } from '../features/live/connectors'

const USAGE = {
  runs_today: { used: 3, limit: 200, remaining: 197 },
  datasets: { used: 1, limit: 20, remaining: 19 },
  dataset_bytes: { used: 48_250, limit: 50_000_000, remaining: 49_951_750 },
  not_tracked: [],
}

const DETAIL = {
  id: 'r2',
  goal: 'Why did revenue change?',
  dataset_name: 'sample sales dataset',
  state: 'completed',
  report_language: 'ar',
  reports: [
    { type: 'descriptive', question: '', title: '', headline: 'ارتفعت الإيرادات', content: '' },
    { type: 'diagnostic', question: '', title: '', headline: '', content: '' },
  ],
}

/** Answer each API path with its own body; anything else is a 404. */
function serve(bodies: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn((path: string) => {
      const body = bodies[path]
      return Promise.resolve({
        ok: body !== undefined,
        status: body !== undefined ? 200 : 404,
        json: () => Promise.resolve(body ?? { detail: 'Not found.' }),
      } as Response)
    }),
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

describe('authenticated live source form', () => {
  it.each(['maintenance-export', ''])('submits only the optional operator alias (%s)', async (alias) => {
    const user = userEvent.setup()
    serve({ '/api/connectors': { connectors: [] } })
    const create = vi.spyOn(connectorsApi, 'create').mockImplementation(async (body) => ({
      id: 'source-1', ...body, sheet: null, profile: null, enabled: true,
      last_status: null, last_error: null, last_checked_at: null,
      last_dataset_id: null, last_run_id: null, next_due_at: null,
      failures: 0, created_at: '', updated_at: '',
    }) as Connector)
    render(<ConnectorsPanel />)
    await screen.findByText('No live sources yet.')
    await user.click(screen.getByText('Add a live source'))
    await user.type(screen.getByLabelText('Name', { exact: true }), 'Maintenance export')
    await user.type(screen.getByLabelText('Address (https)'), 'https://data.example.com/export.csv')
    const field = screen.getByLabelText('Credential alias (optional)')
    expect(field).toHaveAccessibleDescription(/alias supplied by your operator/i)
    if (alias) await user.type(field, alias)
    await user.click(screen.getByRole('button', { name: /^Add source$/ }))
    expect(create).toHaveBeenCalledWith(expect.objectContaining({ credential_id: alias || null }))
    const submitted = create.mock.calls[0][0]
    expect(submitted).not.toHaveProperty('token')
    expect(submitted).not.toHaveProperty('token_env')
    expect(submitted).not.toHaveProperty('headers')
  })
})

describe('OverviewView', () => {
  it('offers the sample data and an upload before anything is analysed', async () => {
    const user = userEvent.setup()
    serve({ '/api/runs': { runs: [] }, '/api/usage': USAGE })
    const onStart = vi.fn()
    render(<OverviewView onOpenRun={vi.fn()} onStart={onStart} />)

    expect(await screen.findByText('Nothing analysed yet')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Try the sample data' }))
    expect(onStart).toHaveBeenLastCalledWith(null)
    await user.click(screen.getByRole('button', { name: 'Add a dataset' }))
    expect(onStart).toHaveBeenLastCalledWith({ kind: 'upload' })
  })

  it('offers no way to start an analysis in the view-only demo', async () => {
    serve({ '/api/runs': { runs: [] }, '/api/usage': USAGE })
    render(<OverviewView onOpenRun={vi.fn()} onStart={vi.fn()} canStart={false} onOpenDashboard={vi.fn()} />)
    expect(await screen.findByText('Nothing analysed yet')).toBeInTheDocument()
    for (const name of ['Try the sample data', 'Add a dataset', 'Start an analysis'])
      expect(screen.queryByRole('button', { name })).toBeNull()
  })

  it('shows the figures, the latest headlines in their own language, and the approval queue', async () => {
    const user = userEvent.setup()
    serve({
      '/api/runs': {
        runs: [
          {
            id: 'r1',
            goal: 'Publish the Q4 review',
            dataset_name: 'q4.csv',
            state: 'awaiting_approval',
            created_at: '2026-10-15T09:00:00+00:00',
            updated_at: '2026-10-15T09:05:00+00:00',
          },
          {
            id: 'r2',
            goal: 'Why did revenue change?',
            dataset_name: 'sample sales dataset',
            state: 'completed',
            created_at: '2026-10-16T09:00:00+00:00',
            updated_at: '2026-10-16T09:05:00+00:00',
          },
        ],
      },
      '/api/runs/r2': DETAIL,
      '/api/usage': USAGE,
    })
    const onOpenRun = vi.fn()
    render(<OverviewView onOpenRun={onOpenRun} onStart={vi.fn()} />)

    const headline = await screen.findByText('ارتفعت الإيرادات')
    // The report's language, not the interface's, so it is read correctly.
    expect(headline).toHaveAttribute('lang', 'ar')
    expect(headline).toHaveAttribute('dir', 'rtl')
    // A report with no headline is left out rather than shown blank.
    expect(screen.queryByText('Diagnostic')).not.toBeInTheDocument()

    const figures = screen.getByText('Waiting for approval').closest('.kpi') as HTMLElement
    expect(within(figures).getByText('1')).toBeInTheDocument()
    expect(figures).toHaveClass('kpi--attention')
    expect(screen.getByText('of 200')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Publish the Q4 review.*Review/ }))
    expect(onOpenRun).toHaveBeenCalledWith('r1')
  })

  it('says so and offers a retry when the runs cannot be read', async () => {
    serve({ '/api/usage': USAGE })
    render(<OverviewView onOpenRun={vi.fn()} onStart={vi.fn()} />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Not found.')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })

  it.each(['running', 'completed'])('opens the observed %s workflow from the populated overview', async (state) => {
    const user = userEvent.setup()
    const onOpenRun = vi.fn()
    const runs = [
      { id: 'new', state: 'cancelled', updated_at: '2026-10-21T12:00:00Z', goal: 'Cancelled request' },
      { id: 'observed', state, updated_at: '2026-10-21T11:00:00Z', goal: 'Observed analysis' },
    ]
    serve({
      '/api/runs': { runs },
      '/api/usage': USAGE,
      '/api/runs/observed': DETAIL,
    })
    render(<OverviewView onOpenRun={onOpenRun} onStart={vi.fn()} onOpenDashboard={vi.fn()} />)
    await user.click(await screen.findByRole('button', { name: /Inspect agent workflow/ }))
    // Prefer a queued/running workflow; otherwise the most recent recorded run.
    expect(onOpenRun).toHaveBeenCalledWith(state === 'running' ? 'observed' : 'new')
  })
})

describe('DatasetsView', () => {
  it('hides adding and analysing in the view-only demo, and keeps them otherwise', async () => {
    const dataset = { id: 'ds1', sha256: '1a2b3c4d5e6f', name: 'fleet.csv', byte_size: 1_000, created_at: '2026-10-16T09:00:00+00:00' }
    serve({ '/api/datasets': { datasets: [dataset] }, '/api/usage': USAGE })
    const { unmount } = render(<ReadOnlyContext.Provider value><DatasetsView onAnalyse={vi.fn()} /></ReadOnlyContext.Provider>)
    expect(await screen.findByText('fleet.csv')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add a dataset' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Analyse fleet.csv' })).toBeNull()
    unmount()
    render(<DatasetsView onAnalyse={vi.fn()} />)
    expect(await screen.findByRole('button', { name: 'Analyse fleet.csv' })).toBeInTheDocument()
  })

  it('explains where datasets come from when there are none', async () => {
    serve({ '/api/datasets': { datasets: [] }, '/api/usage': USAGE })
    render(<DatasetsView onAnalyse={vi.fn()} />)
    expect(await screen.findByText('No datasets yet')).toBeInTheDocument()
  })

  it('analyses a stored dataset by reference', async () => {
    const user = userEvent.setup()
    const dataset = {
      id: 'ds1',
      sha256: '1a2b3c4d5e6f',
      name: 'quarterly-sales.csv',
      byte_size: 48_250,
      created_at: '2026-10-16T09:00:00+00:00',
    }
    serve({ '/api/datasets': { datasets: [dataset] }, '/api/usage': USAGE })
    const onAnalyse = vi.fn()
    render(<DatasetsView onAnalyse={onAnalyse} />)

    const row = (await screen.findByText('quarterly-sales.csv')).closest('li')!
    expect(within(row).getByText('48.3 kB')).toBeInTheDocument()
    expect(within(row).getByText('fingerprint 1a2b3c4d')).toBeInTheDocument()
    // The allowance reads as coloured tiles, and the file limits wait in a fold.
    const storage = (await screen.findByText('Storage used')).closest<HTMLElement>('.kpi')!
    expect(storage).toHaveAttribute('data-hue', 'violet')
    expect(within(storage).getByText('48.3 kB')).toBeVisible()
    expect(within(screen.getByText('Datasets stored').closest<HTMLElement>('.kpi')!).getByText('of 20')).toBeVisible()
    expect(screen.queryByText(/Every dataset you have added/)).not.toBeInTheDocument()
    expect(screen.getByText(/Up to 4 MB/).closest('details')).not.toHaveAttribute('open')
    await user.click(screen.getByRole('button', { name: 'Analyse quarterly-sales.csv' }))
    expect(onAnalyse).toHaveBeenCalledWith(dataset)
  })

  it('adds a file through the API and lists it with its format and rows', async () => {
    const user = userEvent.setup()
    const stored = {
      id: 'ds2',
      sha256: 'abcdef1234',
      name: 'book.xlsx',
      byte_size: 900,
      created_at: '2026-10-16T09:00:00+00:00',
      source_format: 'xlsx',
      row_count: 4,
      column_count: 3,
    }
    let listed: unknown[] = []
    const fetchMock = vi.fn((path: string, init?: RequestInit) => {
      if (path.startsWith('/api/datasets?') && init?.method === 'POST') {
        listed = [stored]
        return Promise.resolve({
          ok: true,
          status: 201,
          json: () =>
            Promise.resolve({
              dataset: stored,
              created: true,
              columns: ['team', 'quarter', 'sales'],
              preview: [],
              warnings: ['Read the sheet “Sales”, the first of 2.'],
              sheets: ['Sales', 'Notes'],
            }),
        } as Response)
      }
      // The live sources panel (ADR 0034): none saved, and no event stream.
      if (path === '/api/events') return Promise.resolve({ ok: false, status: 503 } as Response)
      const body =
        path === '/api/connectors'
          ? { connectors: [] }
          : path === '/api/datasets'
          ? { datasets: listed }
          : path.startsWith('/api/datasets/ds2')
            ? {
                dataset: stored,
                columns: [],
                preview: [],
                row_count: 4,
                profiled_rows: 4,
                mapping: null,
                suggestion: { roles: {}, measure: null, dimension: null, date_order: 'auto', grain: 'auto' },
              }
            : USAGE
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) } as Response)
    })
    vi.stubGlobal('fetch', fetchMock)
    const { container } = render(<DatasetsView onAnalyse={vi.fn()} />)
    expect(await screen.findByText('No datasets yet')).toBeInTheDocument()

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    await user.upload(input, new File(['PK'], 'book.xlsx'))

    expect(await screen.findByText('Added book.xlsx: 4 data rows.')).toBeInTheDocument()
    expect(screen.getByText('Read the sheet “Sales”, the first of 2.')).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Analyse book.xlsx' })).toBeInTheDocument()
    expect(screen.getByText(/^Excel ·/)).toBeInTheDocument()
    // A new upload opens its columns, without taking focus from the status.
    const heading = await screen.findByRole('heading', { name: 'Columns of book.xlsx' })
    expect(heading).not.toHaveFocus()
  })
})
