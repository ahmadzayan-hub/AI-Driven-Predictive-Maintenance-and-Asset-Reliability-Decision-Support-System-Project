import type { RunDetail, RunSummary, RunTask } from '../../shared/types'

export interface AssetEvidence {
  run: RunDetail
  screen: RunTask
  risk: RunTask | null
}

/** Search the complete bounded run list with at most eight reads in flight.
 * Stop only after inspecting every newer candidate; failures remain visible. */
export async function loadAssetEvidence(runs: RunSummary[], getRun: (id: string) => Promise<RunDetail>, cancelled = () => false) {
  const candidates = [...runs].sort((a, b) => b.updated_at.localeCompare(a.updated_at))
  let incomplete = false
  for (let offset = 0; offset < candidates.length && !cancelled(); offset += 8) {
    const results = await Promise.allSettled(candidates.slice(offset, offset + 8).map((run) => getRun(run.id)))
    incomplete ||= results.some((result) => result.status === 'rejected')
    const evidence = findAssetEvidence(results.flatMap((result) => result.status === 'fulfilled' ? [result.value] : []))
    if (evidence) return { evidence, incomplete }
  }
  return { evidence: null, incomplete }
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
