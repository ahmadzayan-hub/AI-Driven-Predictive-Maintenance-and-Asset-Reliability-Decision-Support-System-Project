import { fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '../../shared/api'
import { OverviewView } from './OverviewView'
import type { RunSummary } from '../../shared/types'

afterEach(() => vi.restoreAllMocks())
const renderView = () => render(<OverviewView onOpenRun={vi.fn()} onStart={vi.fn()} />)
const source: RunSummary = { id: 'synthetic-running', state: 'running', dataset_name: 'Synthetic fleet', goal: 'Synthetic test', created_at: '', updated_at: '' }

describe('unknown is not zero', () => {
  it('does not show a zero or next-run action while runs are loading', () => {
    vi.spyOn(api, 'listRuns').mockImplementation(() => new Promise(() => {}))
    vi.spyOn(api, 'usage').mockImplementation(() => new Promise(() => {}))
    const { container } = renderView()
    expect(container.querySelector('.kpi__value')).toBeNull()
    expect(container.querySelector('.next-action')).toBeNull()
    expect(screen.getByRole('status')).toBeInTheDocument()
  })
  it('does not show zero counts or claim no runs after a read failure', async () => {
    vi.spyOn(api, 'listRuns').mockRejectedValue(new Error('Synthetic connection failure'))
    vi.spyOn(api, 'usage').mockImplementation(() => new Promise(() => {}))
    const { container } = renderView()
    await screen.findByRole('alert')
    expect(container.querySelector('.kpi__value')).toBeNull()
    expect(container.querySelector('.next-action')).toBeNull()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
  it('keeps missing quota data unavailable rather than inventing zeros', async () => {
    vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [source] })
    vi.spyOn(api, 'usage').mockRejectedValue(new Error('Synthetic usage outage'))
    renderView()
    const tile = (await screen.findByText('Datasets stored')).closest('.kpi')!
    expect(within(tile as HTMLElement).getByText('—')).toBeInTheDocument()
    expect(within(tile as HTMLElement).queryByText('0')).toBeNull()
  })
})

it('links pending review counts to their actual queue with no invented owner or target', async () => {
  vi.spyOn(api, 'listRuns').mockResolvedValue({ runs: [{ ...source, state: 'awaiting_approval' }] })
  vi.spyOn(api, 'usage').mockRejectedValue(new Error('Synthetic usage outage'))
  vi.spyOn(api, 'getRun').mockRejectedValue(new Error('Synthetic detail outage'))
  vi.spyOn(api, 'runExecutive').mockRejectedValue(new Error('Synthetic brief outage'))
  const onApprovals = vi.fn()
  render(<OverviewView onOpenRun={vi.fn()} onStart={vi.fn()} onApprovals={onApprovals} />)
  const tile = (await screen.findByText('Waiting for approval')).closest('.kpi') as HTMLElement
  expect(within(tile).getByText(/Owner unassigned; no performance target/)).toHaveTextContent('/api/runs')
  fireEvent.click(screen.getByText('Workspace totals'))
  fireEvent.click(within(tile).getByRole('button', { name: 'Review' }))
  expect(onApprovals).toHaveBeenCalledOnce()
})
