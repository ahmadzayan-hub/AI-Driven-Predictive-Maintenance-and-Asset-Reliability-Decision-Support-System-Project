/* What the Overview says about a list of runs. Kept apart from the view
   so the counting a reader relies on can be tested on its own. */
import type { RunSummary } from '../../shared/types'

/** The most runs GET /api/runs returns. A count over a full page is a
 *  count over the most recent runs, and the view says so. */
export const RUN_PAGE = 50

const FINISHED = new Set(['completed', 'partially_completed'])
const ACTIVE = new Set(['queued', 'running'])

export interface RunCounts {
  finished: number
  waiting: number
  active: number
  /** True when the list may be cut off at the page size. */
  capped: boolean
}

export function countRuns(runs: RunSummary[]): RunCounts {
  return {
    finished: runs.filter((run) => FINISHED.has(run.state)).length,
    waiting: runs.filter((run) => run.state === 'awaiting_approval').length,
    active: runs.filter((run) => ACTIVE.has(run.state)).length,
    capped: runs.length >= RUN_PAGE,
  }
}

/** The run whose findings the Overview shows: the most recently updated
 *  one that has reports. A run waiting for approval has them already;
 *  its state is shown beside them, so nothing reads as approved that
 *  was not. */
export function latestWithFindings(runs: RunSummary[]): RunSummary | null {
  const candidates = runs.filter(
    (run) => FINISHED.has(run.state) || run.state === 'awaiting_approval',
  )
  if (candidates.length === 0) return null
  return candidates.reduce((latest, run) => (run.updated_at > latest.updated_at ? run : latest))
}

/** Runs held at the approval gate, oldest first: the longest wait is
 *  the first to deal with. */
export function waitingForApproval(runs: RunSummary[]): RunSummary[] {
  return runs
    .filter((run) => run.state === 'awaiting_approval')
    .sort((a, b) => (a.created_at < b.created_at ? -1 : a.created_at > b.created_at ? 1 : 0))
}

/** The newest runs by last update. */
export function recentRuns(runs: RunSummary[], limit = 5): RunSummary[] {
  return [...runs]
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : a.updated_at > b.updated_at ? -1 : 0))
    .slice(0, limit)
}

/** How many analyses were started on each of the last `days` UTC days,
 *  oldest first, with the total of the `days` before that for comparison.
 *  Counted from the runs' own created_at; a run with no readable date
 *  is left out rather than placed on a day. */
export function dailyStarts(runs: RunSummary[], days = 14, today = new Date()): { counts: number[]; total: number; previous: number } {
  const end = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate())
  const day = 86_400_000
  const counts = Array<number>(days).fill(0)
  let previous = 0
  for (const run of runs) {
    const started = Date.parse(run.created_at)
    if (Number.isNaN(started)) continue
    const age = Math.floor((end - Date.UTC(new Date(started).getUTCFullYear(), new Date(started).getUTCMonth(), new Date(started).getUTCDate())) / day)
    if (age < 0) continue
    if (age < days) counts[days - 1 - age] += 1
    else if (age < 2 * days) previous += 1
  }
  return { counts, total: counts.reduce((a, b) => a + b, 0), previous }
}

/** The hour's greeting key: morning before noon, afternoon before six. */
export function greetingKey(hour: number): 'morning' | 'afternoon' | 'evening' {
  return hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'
}
