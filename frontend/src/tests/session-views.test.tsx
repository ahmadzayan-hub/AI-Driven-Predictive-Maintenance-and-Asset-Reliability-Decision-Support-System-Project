import { render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ActivityView } from '../features/activity/ActivityView'
import { MemoryView } from '../features/memory/MemoryView'
import type { SessionState } from '../shared/types'

const ok = () => Promise.resolve({ ok: true as const, message: '' })

function session(): SessionState {
  return { session_id: 's1', agent_name: 'Agentic OS', version: 'test', welcome: '',
    ended: false, created_at: '2026-10-21T00:00:00Z', transcript: [],
    preferences: {}, memory: {}, memory_entries: [], history: [],
    memory_persisted: true, commands: [] }
}

afterEach(() => vi.unstubAllGlobals())

describe('MemoryView', () => {
  it('colours each kind of memory and keeps internal keys off the screen', () => {
    render(<MemoryView
      entries={[
        { key: 'memory_1', text: 'Report downtime in hours', category: 'preferences', updated: null },
        { key: 'memory_2', text: 'North depot is the pilot site', category: 'work', updated: null },
        { key: 'memory_3', text: 'Fleet review every Monday', category: 'general', updated: null },
      ]}
      disabled={false} onAdd={ok} onUpdate={ok} onDelete={ok} onClearAll={ok} onExport={ok} onClearHistory={vi.fn()} />)
    const hue = (text: string) => within(screen.getByText(text).closest('li')!).getByText(/^(Preferences|Work|General)$/)
    expect(hue('Report downtime in hours')).toHaveAttribute('data-hue', 'violet')
    expect(hue('North depot is the pilot site')).toHaveAttribute('data-hue', 'magenta')
    expect(hue('Fleet review every Monday')).not.toHaveAttribute('data-hue')
    // The key still names the controls for assistive technology, but is not shown.
    expect(screen.queryByText('memory_1')).not.toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /memory_1/ })).toHaveLength(2)
    expect(screen.queryByText(/Review and control what the agent remembers/)).not.toBeInTheDocument()
  })
})

describe('ActivityView', () => {
  it('explains health only when something is wrong, and colours the usage meters', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({
      runs_today: { used: 3, limit: 200, remaining: 197 },
      datasets: { used: 1, limit: 20, remaining: 19 },
      dataset_bytes: { used: 48_250, limit: 50_000_000, remaining: 49_951_750 },
      not_tracked: [],
    }) } as Response)))
    const { rerender } = render(<ActivityView events={[]} session={session()} status="ready" lastSyncedAt={null} />)
    expect(screen.getByText('Agent online')).toBeVisible()
    expect(screen.queryByText(/Connected and responsive/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Memory is saved to/)).not.toBeInTheDocument()
    const meters = await screen.findAllByRole('meter')
    expect(meters.map((meter) => meter.closest('li')!.getAttribute('data-hue'))).toEqual(['teal', 'violet', 'magenta'])
    // A problem still says what is wrong.
    rerender(<ActivityView events={[]} session={session()} status="offline" lastSyncedAt={null} />)
    expect(screen.getByText('Agent offline').nextElementSibling).not.toBeNull()
  })
})
