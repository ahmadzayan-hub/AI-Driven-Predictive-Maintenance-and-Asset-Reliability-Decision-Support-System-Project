import type { RunDetail, RunTask } from '../../shared/types'

export interface AssetEvidence {
  run: RunDetail
  screen: RunTask
  risk: RunTask | null
  /** The decision stages of 31 October (R1 to R3), as the server returned them. */
  decisions: RunTask[]
  /** The cleaner's data-health claim (R4), in the run's language. */
  health: string | null
}

const DECISIONS = ['reliability_model', 'risk_ranking', 'what_if_scenarios']

/** Only stages actually returned by the server can become UI evidence. */
export function findAssetEvidence(runs: RunDetail[]): AssetEvidence | null {
  for (const run of [...runs].sort((a, b) => b.updated_at.localeCompare(a.updated_at))) {
    const screen = run.tasks?.find((task) =>
      task.role === 'rail_asset_manager' && task.state === 'succeeded')
    if (screen) {
      return {
        run,
        screen,
        risk: run.tasks.find((task) => task.role === 'maintenance_risk') ?? null,
        decisions: DECISIONS.flatMap((role) => run.tasks.filter((task) =>
          task.role === role && task.state === 'succeeded' && task.claims.length)),
        health: ((claim) => claim ? claim.text_ar ?? claim.text : null)(run.tasks
          .find((task) => task.role === 'cleaner')?.claims.find((c) => c.id === 'cl_health')),
      }
    }
  }
  return null
}
