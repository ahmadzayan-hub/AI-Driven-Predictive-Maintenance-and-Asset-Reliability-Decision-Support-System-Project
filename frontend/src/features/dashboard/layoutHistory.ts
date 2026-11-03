import type { LayoutResult, LayoutSection } from '../../shared/types'

/** The layouts kept for one run (ADR 2026-11-03-generative-layout): up to five
 *  versions for the same schema fingerprint, the one shown, and pinned section
 *  ids. A schema change starts afresh; pins never outlive the schema they were
 *  validated against. Kept in this browser only. */
export interface LayoutHistory {
  fingerprint: string
  versions: Array<{ result: LayoutResult; at: string }>
  current: number
  pinned: string[]
}

export const MAX_VERSIONS = 5
const key = (runId: string) => `aos-layout:${runId}`

export function readHistory(runId: string): LayoutHistory | null {
  try {
    const value = JSON.parse(localStorage.getItem(key(runId)) ?? 'null') as LayoutHistory | null
    return value && Array.isArray(value.versions) && value.versions.length ? value : null
  } catch { return null }
}

export function writeHistory(runId: string, history: LayoutHistory) {
  try { localStorage.setItem(key(runId), JSON.stringify(history)) } catch { /* private mode: keep in memory only */ }
}

export function sectionsOf(history: LayoutHistory): LayoutSection[] {
  return history.versions[history.current]?.result.plan.sections ?? []
}

/** Add a newly designed layout. Pinned sections of the shown layout carry over,
 *  first, when the schema is the same and the new plan does not already hold them. */
export function addVersion(history: LayoutHistory | null, result: LayoutResult, at: string): LayoutHistory {
  if (!history || history.fingerprint !== result.fingerprint) {
    return { fingerprint: result.fingerprint, versions: [{ result, at }], current: 0, pinned: [] }
  }
  const ids = new Set(result.plan.sections.map((s) => s.id))
  const carried = sectionsOf(history).filter((s) => history.pinned.includes(s.id) && !ids.has(s.id))
  const merged = { ...result, plan: { ...result.plan, sections: [...carried, ...result.plan.sections] } }
  const versions = [...history.versions, { result: merged, at }].slice(-MAX_VERSIONS)
  return { ...history, versions, current: versions.length - 1 }
}

export function restore(history: LayoutHistory, index: number): LayoutHistory {
  return index >= 0 && index < history.versions.length ? { ...history, current: index } : history
}

export function togglePin(history: LayoutHistory, id: string): LayoutHistory {
  const pinned = history.pinned.includes(id) ? history.pinned.filter((p) => p !== id) : [...history.pinned, id]
  return { ...history, pinned }
}
