import type { RunDetail, RunTask } from '../../shared/types'

export interface AssetEvidence {
  run: RunDetail
  screen: RunTask
  risk: RunTask | null
}

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
      }
    }
  }
  return null
}
