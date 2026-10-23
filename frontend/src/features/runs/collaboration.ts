import type { RunDetail, RunTask } from '../../shared/types'
import type { RunEvent } from './runEvents'

const DONE = new Set(['succeeded', 'skipped', 'failed', 'cancelled'])
export const FLOW_ZOOM_MIN = .8
export const FLOW_ZOOM_MAX = 1.4

export function changeFlowZoom(current: number, step: number): number {
  return Math.min(FLOW_ZOOM_MAX, Math.max(FLOW_ZOOM_MIN, Math.round((current + step) * 10) / 10))
}

/** Direction represents the observed stage state, not a recorded message.
 * A start points toward the stage; a returned outcome points toward Hermes. */
export function handoffDirection(event?: RunEvent): 'outbound' | 'inbound' | null {
  if (event?.kind !== 'stage.changed') return null
  if (event.state === 'running') return 'outbound'
  if (DONE.has(event.state) || event.state === 'awaiting_approval') return 'inbound'
  return null
}

export function finishedTasks(tasks: RunTask[]): number {
  return tasks.filter((task) => DONE.has(task.state)).length
}

/** Prioritise a real interruption; never turn a pending stage into "working". */
export function focusTask(tasks: RunTask[]): RunTask | undefined {
  return tasks.find((task) => task.state === 'failed')
    ?? tasks.find((task) => task.state === 'awaiting_approval')
    ?? tasks.find((task) => task.state === 'running')
    ?? [...tasks].reverse().find((task) => DONE.has(task.state))
    ?? tasks[0]
}

export function groupState(tasks: RunTask[]): string {
  for (const state of ['failed', 'awaiting_approval', 'running', 'cancelled', 'pending']) {
    if (tasks.some((task) => task.state === state)) return state
  }
  if (tasks.some((task) => task.state === 'succeeded')) return 'succeeded'
  return tasks[0]?.state ?? 'pending'
}

/** Keep only this run's retained observations. No inferred stage starts,
 *  message contents or synthetic timestamps are added for the visualisation. */
export function collaborationEvents(run: RunDetail, events: RunEvent[]): RunEvent[] {
  const tasks = new Set(run.tasks.map((task) => task.id))
  return events.filter((event) => event.runId === run.id
    && (event.kind !== 'stage.changed' || tasks.has(event.subject)))
}

export function isWorking(run: RunDetail, interrupted: boolean): boolean {
  return run.state === 'running' && !run.paused && !interrupted
    && run.tasks.some((task) => task.state === 'running')
}
