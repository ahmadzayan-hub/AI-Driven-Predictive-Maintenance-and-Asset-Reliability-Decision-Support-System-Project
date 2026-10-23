import type { RunDetail, RunTask } from '../../shared/types'

export interface AssetEvidence {
  run: RunDetail
  screen: RunTask
  risk: RunTask | null
}

/** One server answer (U10): the newest run with a succeeded asset screen,
 * or none. `capped` is the server's own word on whether older runs were
 * left unread. */
export async function loadAssetEvidence(getEvidence: () => Promise<{ run: RunDetail | null; capped: boolean }>) {
  const answer = await getEvidence()
  return { evidence: answer.run ? findAssetEvidence([answer.run]) : null, capped: answer.capped }
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
