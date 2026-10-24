import type { KpiMeasure } from './types'

const MAX_KPIS = 6
const FAMILY_ORDER = ['reliability', 'execution', 'cost']

/** The measures worth a tile: every one with a verdict first, then the
 *  first of each family, so a reader sees reliability, work and cost
 *  even when no target is set. Never more than six. */
export function pickMeasures(measures: KpiMeasure[]): KpiMeasure[] {
  const assessed = measures.filter((m) => ['good', 'okay', 'bad'].includes(m.assessment?.status ?? ''))
  const chosen = [...assessed]
  for (const family of FAMILY_ORDER) {
    const first = measures.find((m) => m.family === family && !chosen.includes(m))
    if (first) chosen.push(first)
  }
  for (const measure of measures) {
    if (chosen.length >= MAX_KPIS) break
    if (!chosen.includes(measure)) chosen.push(measure)
  }
  return chosen.slice(0, MAX_KPIS)
}

