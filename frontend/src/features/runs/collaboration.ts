import type { RunDetail, RunTask } from '../../shared/types'
import type { RunEvent } from './runEvents'

const DONE = new Set(['succeeded', 'skipped', 'failed', 'cancelled'])

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
