import type { RunDetail } from '../../shared/types'

/** A truthful status for a specific run, not a score for an AI model.
 * Pending is deliberately fail-closed if any stage failed or if the
 * independent validator did not record at least one passing check. */
export function summarizeRunEvidence(run: Pick<RunDetail, 'tasks'> | null) {
  if (!run) return { status: 'unavailable' as const, completed: 0, total: 0 }
  // Older API payloads, partial responses and test fixtures may omit tasks.
  // Fail closed rather than crashing the executive overview.
  const stages = (Array.isArray(run.tasks) ? run.tasks : [])
    .filter((task) => task.role !== 'publish')
  const completed = stages.filter((task) => task.state === 'succeeded').length
  const validator = stages.find((task) => task.role === 'validator')
  const passed = stages.length > 0
    && completed === stages.length
    && validator?.state === 'succeeded'
    && validator.quality_checks.length > 0
    && validator.quality_checks.every((check) => check.passed)
  return {
    status: passed ? 'passed' as const : 'pending' as const,
    completed,
    total: stages.length,
  }
}
