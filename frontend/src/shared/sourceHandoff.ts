import type { RunDetail } from './types'

/** Source presence is not approval or permission to create/execute work. */
export function hasWorkSource(run: Pick<RunDetail, 'state' | 'dataset_id'>): boolean {
  return typeof run.dataset_id === 'string' && !!run.dataset_id.trim() && ['awaiting_approval', 'completed'].includes(run.state)
}
