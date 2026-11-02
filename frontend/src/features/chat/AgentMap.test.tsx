import { act, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { AgentMap } from './AgentMap'
import { JarvisCore } from './JarvisCore'
import { api } from '../../shared/api'
import type { RunDetail, RunTask } from '../../shared/types'

const task = (role: string, state: string, title: string): RunTask =>
  ({ id: role, role, title, state, summary: null, quality_checks: [], claims: [] })
const run = (state: string, tasks: RunTask[]) => ({ id: 'r1', state, tasks } as unknown as RunDetail)

afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

it('shows each agent with the state the server reports, grouped by band', async () => {
  vi.spyOn(api, 'getRun').mockResolvedValue(run('awaiting_approval', [
    task('planner', 'succeeded', 'Planner Agent — what to do'), task('anomaly', 'failed', 'Anomaly Agent'),
    task('reliability_model', 'skipped', 'Reliability Agent — failure pattern'),
  ]))
  render(<AgentMap runId="r1" />)
  const map = await screen.findByRole('region', { name: 'Agent map' })
  expect(map).toHaveTextContent('1/3')
  // Built-in agents are named in the interface language; a custom stage keeps the server's title.
  expect(screen.getByText('Planning').closest('li')).toHaveAttribute('data-state', 'succeeded')
  expect(screen.getByText('Anomaly detection').closest('li')).toHaveAttribute('data-state', 'failed')
  expect(screen.getByText('Reliability Agent').closest('li')).toHaveAttribute('data-state', 'skipped')
})

it('refreshes while the run is live and stops once it settles', async () => {
  vi.useFakeTimers()
  const getRun = vi.spyOn(api, 'getRun')
    .mockResolvedValueOnce(run('running', [task('planner', 'running', 'Planner Agent')]))
    .mockResolvedValue(run('completed', [task('planner', 'succeeded', 'Planner Agent')]))
  render(<AgentMap runId="r1" />)
  await act(async () => { await Promise.resolve() })
  expect(screen.getByText('Planning').closest('li')).toHaveAttribute('data-state', 'running')
  await act(async () => { await vi.advanceTimersByTimeAsync(4000) })
  expect(screen.getByText('Planning').closest('li')).toHaveAttribute('data-state', 'succeeded')
  await act(async () => { await vi.advanceTimersByTimeAsync(12000) })
  expect(getRun).toHaveBeenCalledTimes(2)
})

it('says so when agent states cannot be read, inventing none', async () => {
  vi.spyOn(api, 'getRun').mockRejectedValue(new Error('Synthetic outage'))
  render(<AgentMap runId="r1" />)
  expect(await screen.findByText('Agent states unavailable.')).toBeInTheDocument()
})

it('turns the orb into a head outline only while speaking', () => {
  const { container, rerender } = render(<JarvisCore state="ready" />)
  expect(container.querySelector('.jarvis-core__head')).not.toBeNull()
  expect(container.querySelector('.jarvis-core')).toHaveAttribute('data-state', 'ready')
  rerender(<JarvisCore state="speaking" />)
  expect(container.querySelector('.jarvis-core')).toHaveAttribute('data-state', 'speaking')
})
