import type { RunExecutive } from './types'

/** One reading of a model card for every screen that shows one: a card
 *  that was not fitted, has no metric or was judged unsupported is not
 *  assessed; one judged weak or beaten by its baseline is bad; only a
 *  card that beat its baseline is good. Nothing else counts. */
export function modelTone(model: RunExecutive['models'][number]): 'good' | 'bad' | 'unassessed' {
  if (model.fitted === false || !model.metric || model.details.verdict === 'not_supported') return 'unassessed'
  if (model.details.verdict === 'weak' || model.beats_baseline === false) return 'bad'
  return model.beats_baseline === true ? 'good' : 'unassessed'
}
